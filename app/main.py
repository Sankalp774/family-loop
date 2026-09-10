from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import Cookie, Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.agents.desk import run_desk
from app.agents.model import model_label
from app.auth import clear_session, current_user, login, require_parent, start_session
from app.clock import clear_override, iso
from app.clock import set_override as set_clock
from app.clock import this_saturday_morning, this_sunday_evening
from app.ocr import image_to_text
from app.snapshots import parse_app_list
from app.ids import new_id
from app.calendar import family_calendar
from app.config import ASK_FIRST_CHOICES, HARD_NO_CHOICES, KIND_CHOICES, LOCK_ITEMS, PARENT_NOTE_DEFAULT, ROOT
from app.policy import policy_from_answers
from app.intelligence import resolve_exception
from app.seed import seed
from app.simulate import fast_forward, saturday_simulation
from app.store import get_store
from app.events import add_event, calendar_meta, delete_event, patch_event
from app.todos import add_todo, delete_todo, patch_todo
from app.views import public_state

STATIC = ROOT / "static"

app = FastAPI(
    title="Family Loop",
    description="Phones enforce. Agents remind, compare, and ask. Parent only shows up for a real yes/no.",
    version="0.1.0",
)


class LoginBody(BaseModel):
    email: str
    password: str


class SetupBody(BaseModel):
    age: int = 13
    school_hours: dict[str, str] = Field(
        default_factory=lambda: {"start": "08:00", "end": "15:00"}
    )
    ask_first: list[str] = Field(
        default_factory=lambda: ["new_app", "new_contact", "social", "in_app_purchase"]
    )
    hard_no: list[str] = Field(default_factory=lambda: ["gambling", "dating"])
    youtube_after_homework: bool = True
    sports_phone_preset: bool = True
    daily_cap_minutes: int = 120
    notes: str = PARENT_NOTE_DEFAULT
    approved_apps: list[str] | None = None
    sports_days: list[int] | None = None
    sports_hours: dict[str, str] | None = None
    homework_done_after: str | None = None
    child_name: str | None = None


class FamilyBody(BaseModel):
    parent_name: str | None = None
    child_name: str | None = None
    city: str | None = None


class AskPatch(BaseModel):
    status: str | None = None
    parent_note: str | None = None
    subject: str | None = None
    detail: str | None = None


class OutboxBody(BaseModel):
    body: str
    channel: str = "whatsapp"


class LocksBody(BaseModel):
    screen_time_on: bool = False
    ask_to_install: bool = False
    youtube_supervised: bool = False
    roblox_pin: bool = False
    downtime_school_hours: bool = False


class AskBody(BaseModel):
    kind: str
    subject: str
    detail: str = ""
    costs_money: bool = False


class DecideBody(BaseModel):
    status: str
    note: str = ""


class ExceptionBody(BaseModel):
    subject: str
    status: str


class SnapshotBody(BaseModel):
    raw_list: str
    kind: str = "random"


class DeskBody(BaseModel):
    event: str
    payload: dict[str, Any] = Field(default_factory=dict)


class TodoCreate(BaseModel):
    date: str
    title: str


class TodoPatch(BaseModel):
    title: str | None = None
    done: bool | None = None


class EventBody(BaseModel):
    title: str
    date: str
    end_date: str | None = None
    notes: str = ""
    location: str = ""
    all_day: bool = False
    start_time: str | None = None
    end_time: str | None = None
    calendar: str = "family"
    who: str = "family"
    repeat: str = "none"
    repeat_until: str | None = None
    important: bool = False


class EventPatch(BaseModel):
    title: str | None = None
    date: str | None = None
    end_date: str | None = None
    notes: str | None = None
    location: str | None = None
    all_day: bool | None = None
    start_time: str | None = None
    end_time: str | None = None
    calendar: str | None = None
    who: str | None = None
    repeat: str | None = None
    repeat_until: str | None = None
    important: bool | None = None


@app.on_event("startup")
def _startup() -> None:
    store = get_store()
    if not store.path.exists() or not store.snapshot().get("family_id"):
        seed("demo")


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "model": model_label(),
        "disclaimer": "We do not control the device.",
    }


@app.get("/api/calendar")
def api_calendar(year: int | None = None, month: int | None = None) -> dict:
    return family_calendar(get_store().snapshot(), year=year, month=month)


@app.get("/api/doors")
def doors() -> dict:
    return {
        "tagline": "Phones enforce. Agents remind, compare, and ask.",
        "disclaimer": "We do not control the device.",
        "choices": {
            "ask_first": ASK_FIRST_CHOICES,
            "hard_no": HARD_NO_CHOICES,
            "kinds": KIND_CHOICES,
            "parent_note_default": PARENT_NOTE_DEFAULT,
        },
        "calendar": family_calendar(get_store().snapshot()),
        "doors": [
            {
                "role": "parent",
                "name": "Meera",
                "email": "meera@familyloop.demo",
                "password": "parent",
                "copy": "Setup, checklist, queue, ping, Sunday.",
            },
            {
                "role": "child",
                "name": "Aarav",
                "email": "aarav@familyloop.demo",
                "password": "aarav",
                "copy": "Asks and Screen Time pastes. Cannot change rules.",
            },
        ],
    }


@app.post("/api/login")
def api_login(body: LoginBody, response: Response) -> dict:
    user = login(body.email, body.password)
    start_session(response, user)
    return {"user": user, "state": public_state(get_store().snapshot(), user["role"])}


@app.post("/api/logout")
def api_logout(
    response: Response, family_loop: Annotated[Optional[str], Cookie()] = None
) -> dict:
    clear_session(response, family_loop)
    return {"ok": True}


@app.get("/api/me")
def api_me(user: Annotated[dict, Depends(current_user)]) -> dict:
    return {
        "user": user,
        "state": public_state(get_store().snapshot(), user["role"]),
        "lock_items": LOCK_ITEMS,
        "model": model_label(),
    }


@app.get("/api/state")
def api_state(user: Annotated[dict, Depends(current_user)]) -> dict:
    return public_state(get_store().snapshot(), user["role"])


@app.post("/api/setup")
def api_setup(body: SetupBody, user: Annotated[dict, Depends(current_user)]) -> dict:
    require_parent(user)
    payload = body.model_dump(exclude_none=True)
    result = run_desk("setup", payload)

    def overlay(data):
        answers = {**(data.get("policy") or {}), **payload}
        data["policy"] = policy_from_answers(answers, data.get("child") or {})
        if payload.get("child_name"):
            data.setdefault("child", {})["name"] = payload["child_name"]
            data["policy"]["child_name"] = payload["child_name"]

    get_store().update(overlay)
    return {"agent": _agent_public(result), "state": public_state(get_store().snapshot(), "parent")}


@app.patch("/api/family")
def api_family(body: FamilyBody, user: Annotated[dict, Depends(current_user)]) -> dict:
    require_parent(user)

    def mutate(data):
        if body.parent_name:
            data.setdefault("parent", {})["name"] = body.parent_name.strip()
        if body.child_name:
            name = body.child_name.strip()
            data.setdefault("child", {})["name"] = name
            if data.get("policy"):
                data["policy"]["child_name"] = name
        if body.city:
            data.setdefault("child", {})["city"] = body.city.strip()

    get_store().update(mutate)
    return {"state": public_state(get_store().snapshot(), "parent")}


@app.post("/api/locks")
def api_locks(body: LocksBody, user: Annotated[dict, Depends(current_user)]) -> dict:
    require_parent(user)
    result = run_desk("locks", body.model_dump())
    return {"agent": _agent_public(result), "state": public_state(get_store().snapshot(), "parent")}


@app.post("/api/asks")
def api_asks(body: AskBody, user: Annotated[dict, Depends(current_user)]) -> dict:
    if user["role"] not in {"child", "parent"}:
        raise HTTPException(status_code=403, detail="Unknown door")
    payload = body.model_dump()
    payload["kid"] = user.get("kid") or "aarav"
    result = run_desk("new_ask", payload)
    return {
        "agent": _agent_public(result),
        "state": public_state(get_store().snapshot(), user["role"]),
    }


@app.post("/api/exceptions")
def api_exception(body: ExceptionBody, user: Annotated[dict, Depends(current_user)]) -> dict:
    require_parent(user)
    result = resolve_exception(body.subject, body.status, by=user.get("name") or "parent")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("reason"))
    return {"ok": True, "state": public_state(get_store().snapshot(), "parent")}


@app.post("/api/asks/{request_id}/decide")
def api_decide(
    request_id: str, body: DecideBody, user: Annotated[dict, Depends(current_user)]
) -> dict:
    require_parent(user)
    payload = body.model_dump()
    payload["request_id"] = request_id
    result = run_desk("decide", payload)
    return {"agent": _agent_public(result), "state": public_state(get_store().snapshot(), "parent")}


@app.patch("/api/asks/{request_id}")
def api_ask_patch(
    request_id: str, body: AskPatch, user: Annotated[dict, Depends(current_user)]
) -> dict:
    require_parent(user)
    found = {"ok": False}

    def mutate(data):
        for req in data.get("requests") or []:
            if req.get("id") != request_id:
                continue
            if body.subject is not None:
                req["subject"] = body.subject.strip()
            if body.detail is not None:
                req["detail"] = body.detail.strip()
            if body.parent_note is not None:
                req["parent_note"] = body.parent_note.strip()
            if body.status in {"pending", "allowed", "denied"}:
                req["status"] = body.status
                if body.status != "pending":
                    req["decided_at"] = iso()
                    req["decided_by"] = "parent"
            found["ok"] = True
            break

    get_store().update(mutate)
    if not found["ok"]:
        raise HTTPException(status_code=404, detail="Ask not found.")
    if body.status in {"allowed", "denied"}:
        run_desk("decide", {"request_id": request_id, "status": body.status, "note": body.parent_note or ""})
    return {"state": public_state(get_store().snapshot(), "parent")}


@app.post("/api/outbox")
def api_outbox(body: OutboxBody, user: Annotated[dict, Depends(current_user)]) -> dict:
    require_parent(user)
    message = {
        "id": new_id("msg"),
        "channel": body.channel,
        "at": iso(),
        "to": "Meera",
        "from": "Family Loop",
        "body": body.body.strip(),
        "simulated": True,
        "label": "Simulated WhatsApp" if body.channel == "whatsapp" else "Simulated email",
        "edited_by": "parent",
    }

    def mutate(data):
        data.setdefault("outbox", []).append(message)

    get_store().update(mutate)
    return {"message": message, "state": public_state(get_store().snapshot(), "parent")}


@app.post("/api/ping")
def api_ping(user: Annotated[dict, Depends(current_user)]) -> dict:
    require_parent(user)
    result = run_desk("ping", {"force": True})
    return {"agent": _agent_public(result), "state": public_state(get_store().snapshot(), "parent")}


@app.post("/api/checkin")
def api_checkin(body: SnapshotBody, user: Annotated[dict, Depends(current_user)]) -> dict:
    payload = body.model_dump()
    payload["kid"] = user.get("kid") or "aarav"
    result = run_desk("snapshot", payload)
    return {
        "agent": _agent_public(result),
        "state": public_state(get_store().snapshot(), user["role"]),
    }


@app.post("/api/ocr")
async def api_ocr(
    user: Annotated[dict, Depends(current_user)],
    image: UploadFile = File(...),
) -> dict:
    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty photo.")
    suffix = Path(image.filename or "shot.png").suffix or ".png"
    try:
        text = image_to_text(data, suffix)
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    apps = parse_app_list(text)
    raw_list = "\n".join(f"{app['name']} {app['minutes']}" for app in apps) or text
    return {
        "text": text,
        "apps": apps,
        "raw_list": raw_list,
        "source": "photo_ocr",
        "disclaimer": "Read from a human photo. We do not control the device.",
    }


@app.post("/api/digest")
def api_digest(user: Annotated[dict, Depends(current_user)]) -> dict:
    require_parent(user)
    result = run_desk("sunday", {})
    return {"agent": _agent_public(result), "state": public_state(get_store().snapshot(), "parent")}


@app.post("/api/desk")
def api_desk(body: DeskBody, user: Annotated[dict, Depends(current_user)]) -> dict:
    require_parent(user)
    result = run_desk(body.event, body.payload)
    return {"agent": _agent_public(result), "state": public_state(get_store().snapshot(), "parent")}


@app.get("/api/calendars")
def api_calendars() -> dict:
    return {"calendars": calendar_meta()}


@app.post("/api/events")
def api_event_add(body: EventBody, user: Annotated[dict, Depends(current_user)]) -> dict:
    result = add_event(body.model_dump(), by=user.get("role") or "parent")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("reason"))
    return {"event": result["event"], "state": public_state(get_store().snapshot(), user["role"])}


@app.patch("/api/events/{event_id}")
def api_event_patch(
    event_id: str, body: EventPatch, user: Annotated[dict, Depends(current_user)]
) -> dict:
    result = patch_event(event_id, body.model_dump(exclude_unset=True), by=user.get("role") or "parent")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("reason"))
    return {"event": result["event"], "state": public_state(get_store().snapshot(), user["role"])}


@app.delete("/api/events/{event_id}")
def api_event_delete(event_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    result = delete_event(event_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("reason"))
    return {"ok": True, "state": public_state(get_store().snapshot(), user["role"])}


@app.post("/api/todos")
def api_todo_add(body: TodoCreate, user: Annotated[dict, Depends(current_user)]) -> dict:
    result = add_todo(body.date, body.title, by=user.get("role") or "parent")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("reason"))
    return {"todo": result["todo"], "state": public_state(get_store().snapshot(), user["role"])}


@app.patch("/api/todos/{todo_id}")
def api_todo_patch(
    todo_id: str, body: TodoPatch, user: Annotated[dict, Depends(current_user)]
) -> dict:
    result = patch_todo(todo_id, title=body.title, done=body.done)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("reason"))
    return {"todo": result["todo"], "state": public_state(get_store().snapshot(), user["role"])}


@app.delete("/api/todos/{todo_id}")
def api_todo_delete(todo_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    result = delete_todo(todo_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("reason"))
    return {"ok": True, "state": public_state(get_store().snapshot(), user["role"])}


@app.post("/api/demo/reset")
def api_reset(user: Annotated[dict, Depends(current_user)]) -> dict:
    require_parent(user)
    seed("demo")
    return {"ok": True, "state": public_state(get_store().snapshot(), "parent")}


@app.post("/api/demo/week")
def api_week(user: Annotated[dict, Depends(current_user)]) -> dict:
    require_parent(user)
    seed("week")
    return {"ok": True, "state": public_state(get_store().snapshot(), "parent")}


@app.post("/api/demo/saturday")
def api_saturday(user: Annotated[dict, Depends(current_user)]) -> dict:
    require_parent(user)
    stamp = set_clock(this_saturday_morning())
    return {"clock": stamp, "state": public_state(get_store().snapshot(), "parent")}


@app.post("/api/demo/sunday")
def api_sunday(user: Annotated[dict, Depends(current_user)]) -> dict:
    require_parent(user)
    stamp = set_clock(this_sunday_evening())
    return {"clock": stamp, "state": public_state(get_store().snapshot(), "parent")}


@app.post("/api/demo/live")
def api_live(user: Annotated[dict, Depends(current_user)]) -> dict:
    require_parent(user)
    clear_override()
    return {"clock": None, "state": public_state(get_store().snapshot(), "parent")}


@app.post("/api/demo/simulate-saturday")
def api_sim_saturday(user: Annotated[dict, Depends(current_user)]) -> dict:
    require_parent(user)
    result = saturday_simulation()
    return {
        "steps": result["steps"],
        "state": public_state(get_store().snapshot(), "parent"),
    }


@app.post("/api/demo/fast-forward")
def api_fast_forward(user: Annotated[dict, Depends(current_user)]) -> dict:
    require_parent(user)
    result = fast_forward()
    return {
        "steps": result["steps"],
        "state": public_state(get_store().snapshot(), "parent"),
    }


def _agent_public(result: dict) -> dict:
    return {
        "event": result.get("event"),
        "model": result.get("model"),
        "used_strands": result.get("used_strands"),
        "used_agent_loop": result.get("used_agent_loop"),
        "text": result.get("text"),
    }


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/architecture.svg")
def architecture() -> FileResponse:
    return FileResponse(ROOT / "docs" / "architecture.svg", media_type="image/svg+xml")
