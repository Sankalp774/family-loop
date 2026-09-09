from __future__ import annotations

import logging
from typing import Any

from strands.hooks import HookProvider, HookRegistry
from strands.hooks.events import AfterInvocationEvent, AfterToolCallEvent, BeforeToolCallEvent

from app.clock import iso
from app.store import get_store

log = logging.getLogger("family_loop.hooks")

FORBIDDEN_CLAIMS = (
    "we locked the phone",
    "we locked the device",
    "family loop locked",
    "i disabled the app",
    "i uninstalled",
    "mdm",
    "family link api",
    "screen time api",
)


class DeskGuardrails(HookProvider):
    """Never let a specialist pretend it is the OS."""

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeToolCallEvent, self.before_tool)
        registry.add_callback(AfterToolCallEvent, self.after_tool)
        registry.add_callback(AfterInvocationEvent, self.after_invoke)

    def before_tool(self, event: BeforeToolCallEvent) -> None:
        name = getattr(event, "tool_use", {}) or {}
        if isinstance(name, dict):
            tool_name = name.get("name")
        else:
            tool_name = getattr(event, "selected_tool", None)
        log.debug("tool starting %s", tool_name)

    def after_tool(self, event: AfterToolCallEvent) -> None:
        tool_use = getattr(event, "tool_use", {}) or {}
        name = tool_use.get("name") if isinstance(tool_use, dict) else "tool"
        result = getattr(event, "result", None) or getattr(event, "tool_result", None)
        summary = _clip(result)
        get_store().log_agent(
            {
                "at": iso(),
                "agent": getattr(getattr(event, "agent", None), "name", None) or "desk",
                "event": "tool",
                "tool": name,
                "summary": summary,
            }
        )

    def after_invoke(self, event: AfterInvocationEvent) -> None:
        result = getattr(event, "result", None)
        text = str(getattr(result, "message", result) or "")
        lowered = text.lower()
        if any(claim in lowered for claim in FORBIDDEN_CLAIMS):
            log.warning("guardrail: model claimed device control")
            get_store().log_agent(
                {
                    "at": iso(),
                    "agent": "guardrail",
                    "event": "blocked_claim",
                    "summary": "Stripped a sentence that claimed Family Loop locked the phone.",
                }
            )


def _clip(value: Any) -> str:
    text = str(value)
    return text if len(text) < 400 else text[:400] + "…"
