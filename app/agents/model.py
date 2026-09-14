from __future__ import annotations

import json
import logging
import os
import re
import uuid
from typing import Any, AsyncIterator, Optional, TypedDict, TypeVar

T = TypeVar("T")

from strands.models import Model
from strands.types.content import Messages
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolSpec

from app.config import (
    AWS_REGION,
    BEDROCK_MODEL_ID,
    LMSTUDIO_BASE_URL,
    LMSTUDIO_MODEL,
    current_model_mode,
)

log = logging.getLogger("family_loop.model")


class DeskRouterModel(Model):
    """Local Strands model: still runs the agent loop and emits real tool-use events.

    Used when Bedrock is not configured so the demo and tests exercise @tool
    specialists. Set FAMILY_LOOP_MODEL=bedrock for the submission.
    """

    class ModelConfig(TypedDict, total=False):
        model_id: str

    def __init__(self) -> None:
        self.config: DeskRouterModel.ModelConfig = {"model_id": "family-loop-desk-router"}

    def update_config(self, **model_config: Any) -> None:
        self.config.update(model_config)

    def get_config(self) -> ModelConfig:
        return self.config

    async def structured_output(
        self,
        output_model: type[T],
        prompt: Messages,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ):
        payload = _extract_json(_last_user_text(prompt))
        try:
            yield {"output": output_model(**payload)}
        except Exception:
            yield {"output": output_model()}

    async def stream(
        self,
        messages: Messages,
        tool_specs: Optional[list[ToolSpec]] = None,
        system_prompt: Optional[str] = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        user_text = _last_user_text(messages)
        tool_result = _last_tool_result_text(messages)
        specs = tool_specs or []

        yield {"messageStart": {"role": "assistant"}}

        if tool_result:
            text = _summarize(tool_result)
            yield {"contentBlockDelta": {"delta": {"text": text}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}
            yield {
                "metadata": {
                    "usage": {
                        "inputTokens": max(len(user_text) // 4, 1),
                        "outputTokens": max(len(text) // 4, 1),
                        "totalTokens": max((len(user_text) + len(text)) // 4, 1),
                    },
                    "metrics": {"latencyMs": 8},
                }
            }
            return

        chosen = _pick_tool(user_text, specs) if specs else None
        if chosen:
            payload = _tool_input(chosen, user_text)
            tool_use_id = f"tooluse_{uuid.uuid4().hex[:8]}"
            name = chosen.get("name")
            yield {
                "contentBlockStart": {
                    "start": {"toolUse": {"toolUseId": tool_use_id, "name": name}}
                }
            }
            yield {
                "contentBlockDelta": {
                    "delta": {"toolUse": {"input": json.dumps(payload)}}
                }
            }
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
            return

        text = (
            "Desk has nothing to file. Parent still has to tick locks on the phone OS. "
            "We do not control the device."
        )
        yield {"contentBlockDelta": {"delta": {"text": text}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "end_turn"}}


def _last_user_text(messages: Messages) -> str:
    for message in reversed(messages or []):
        if message.get("role") != "user":
            continue
        chunks: list[str] = []
        for block in message.get("content") or []:
            if isinstance(block, dict) and "text" in block:
                chunks.append(str(block["text"]))
        if chunks:
            return "\n".join(chunks)
    return ""


def _last_tool_result_text(messages: Messages) -> str | None:
    for message in reversed(messages or []):
        for block in message.get("content") or []:
            if isinstance(block, dict) and "toolResult" in block:
                result = block["toolResult"]
                bits = []
                for item in result.get("content") or []:
                    if "text" in item:
                        bits.append(item["text"])
                    elif "json" in item:
                        bits.append(json.dumps(item["json"]))
                return "\n".join(bits) or json.dumps(result)
    return None


def _summarize(tool_result: str) -> str:
    text = tool_result.strip()
    if len(text) > 1600:
        text = text[:1600] + "…"
    return text


def _pick_tool(user_text: str, specs: list[ToolSpec]) -> ToolSpec | None:
    if not specs:
        return None
    text = user_text.lower()
    event = _event_name(user_text)
    preferred = {
        "setup": ["setup_coach", "save_family_policy", "save_locks_checklist"],
        "locks": ["save_locks_checklist", "setup_coach"],
        "new_ask": ["request_triage", "file_child_request", "triage_child_request"],
        "ping": ["checkin_runner", "issue_random_ping"],
        "snapshot": ["checkin_runner", "save_screen_time_snapshot"],
        "saturday": ["checkin_runner", "save_screen_time_snapshot"],
        "sunday": ["digest_writer", "write_sunday_digest", "send_digest_message"],
        "digest": ["digest_writer", "write_sunday_digest"],
        "override": ["override_clerk", "record_parent_decision"],
        "decide": ["override_clerk", "record_parent_decision"],
        "desk": [],
    }.get(event, [])

    by_name = {str(spec.get("name")): spec for spec in specs}
    for name in preferred:
        if name in by_name:
            return by_name[name]

    scored: list[tuple[int, ToolSpec]] = []
    for spec in specs:
        name = str(spec.get("name") or "")
        desc = str(spec.get("description") or "").lower()
        score = 0
        for token in name.replace("_", " ").split():
            if token and token in text:
                score += 4
        if name.replace("_", " ") in text:
            score += 6
        if event and event in name:
            score += 5
        if event and event in desc:
            score += 2
        scored.append((score, spec))
    scored.sort(key=lambda row: row[0], reverse=True)
    if scored and scored[0][0] > 0:
        return scored[0][1]
    return specs[0]


def _event_name(user_text: str) -> str:
    match = re.search(r"EVENT:\s*([a-z_]+)", user_text, re.I)
    if match:
        return match.group(1).lower()
    return ""


def _tool_input(spec: ToolSpec, user_text: str) -> dict[str, Any]:
    payload = _extract_json(user_text)
    hours = payload.get("school_hours") if isinstance(payload.get("school_hours"), dict) else {}
    if hours:
        payload.setdefault("school_start", hours.get("start", "08:00"))
        payload.setdefault("school_end", hours.get("end", "15:00"))
    schema = (spec.get("inputSchema") or {}).get("json") or spec.get("inputSchema") or {}
    if isinstance(schema, dict) and "json" in schema and isinstance(schema["json"], dict):
        schema = schema["json"]
    props = schema.get("properties") or {}
    required = schema.get("required") or list(props.keys())
    result: dict[str, Any] = {}

    for key, prop in props.items():
        if key in payload:
            result[key] = payload[key]
            continue
        if key in {"query", "payload", "request", "answers"}:
            result[key] = json.dumps(payload) if payload else user_text
            continue
        typ = (prop or {}).get("type")
        if typ == "boolean":
            result[key] = bool(payload.get(key, False))
        elif typ == "integer" or typ == "number":
            result[key] = payload.get(key, 0)
        elif typ == "array":
            result[key] = payload.get(key, [])
        elif typ == "object":
            result[key] = payload.get(key, payload if payload else {})
        else:
            result[key] = payload.get(key, "")

    for key in required:
        if key not in result:
            result[key] = json.dumps(payload) if payload else user_text
    if not result:
        result["query"] = user_text
    return result


def _extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"PAYLOAD:\s*(\{.*\}|\[.*\])", text, re.S)
    blob = match.group(1) if match else None
    if not blob:
        match = re.search(r"(\{.*\})", text, re.S)
        blob = match.group(1) if match else None
    if not blob:
        return {}
    try:
        data = json.loads(blob)
        return data if isinstance(data, dict) else {"value": data}
    except json.JSONDecodeError:
        return {}


def probe_lmstudio() -> dict:
    import json
    import urllib.error
    import urllib.request

    url = f"{LMSTUDIO_BASE_URL}/models"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer lm-studio"})
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "reason": f"LM Studio is not reachable at {LMSTUDIO_BASE_URL} ({exc})."}
    models = [row.get("id") for row in (payload.get("data") or []) if row.get("id")]
    return {
        "ok": True,
        "base_url": LMSTUDIO_BASE_URL,
        "models": models,
        "model_id": LMSTUDIO_MODEL or (models[0] if models else ""),
    }


def _lmstudio_model():
    probe = probe_lmstudio()
    if not probe.get("ok"):
        raise RuntimeError(probe.get("reason") or "LM Studio is not running.")
    model_id = probe.get("model_id") or "local-model"
    from strands.models.openai import OpenAIModel

    log.info("Using LM Studio %s at %s", model_id, LMSTUDIO_BASE_URL)
    return OpenAIModel(
        client_args={
            "api_key": os.environ.get("LMSTUDIO_API_KEY", "lm-studio"),
            "base_url": LMSTUDIO_BASE_URL,
        },
        model_id=model_id,
        params={"temperature": 0.2},
    )


def build_model():
    mode = current_model_mode()
    if mode == "bedrock":
        from strands.models import BedrockModel

        log.info("Using Bedrock model %s in %s", BEDROCK_MODEL_ID, AWS_REGION)
        return BedrockModel(
            model_id=BEDROCK_MODEL_ID,
            region_name=AWS_REGION,
            temperature=0.2,
        )
    if mode == "lmstudio":
        return _lmstudio_model()
    log.info("Using scripted DeskRouterModel (demo-safe; no GPU, no Bedrock)")
    return DeskRouterModel()


def model_label() -> str:
    mode = current_model_mode()
    if mode == "bedrock":
        return f"bedrock:{BEDROCK_MODEL_ID}"
    if mode == "lmstudio":
        probe = probe_lmstudio()
        mid = probe.get("model_id") or LMSTUDIO_MODEL or "local"
        return f"lmstudio:{mid}"
    return "scripted:desk-router"
