from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import TZ_NAME
from app import store as storemod

TZ = ZoneInfo(TZ_NAME)


def live_now() -> datetime:
    """Wall clock. The family calendar always uses this so demo Saturday/Sunday
    buttons cannot cross out a live day such as 11 Sep."""
    return datetime.now(TZ)


def now() -> datetime:
    raw = storemod.get_store().clock_override()
    if raw:
        return datetime.fromisoformat(raw).astimezone(TZ)
    return live_now()


def iso(dt: datetime | None = None) -> str:
    return (dt or now()).isoformat(timespec="seconds")


def set_override(dt: datetime) -> str:
    stamp = dt.astimezone(TZ).isoformat(timespec="seconds")
    storemod.get_store().set_clock(stamp)
    return stamp


def clear_override() -> None:
    storemod.get_store().set_clock(None)


def this_saturday_morning() -> datetime:
    current = now()
    # Monday=0 … Sunday=6. Saturday=5.
    delta = (5 - current.weekday()) % 7
    day = (current + timedelta(days=delta)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    return day


def this_sunday_evening() -> datetime:
    current = now()
    delta = (6 - current.weekday()) % 7
    return (current + timedelta(days=delta)).replace(
        hour=19, minute=0, second=0, microsecond=0
    )


def week_start(dt: datetime | None = None) -> datetime:
    current = dt or now()
    monday = current - timedelta(days=current.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def is_school_hours(dt: datetime | None = None, policy: dict | None = None) -> bool:
    current = dt or now()
    hours = (policy or {}).get("school_hours") or {
        "start": "08:00",
        "end": "15:00",
        "days": [0, 1, 2, 3, 4],
    }
    days = hours.get("days", [0, 1, 2, 3, 4])
    if current.weekday() not in days:
        return False
    start = _hhmm(hours.get("start", "08:00"))
    end = _hhmm(hours.get("end", "15:00"))
    minutes = current.hour * 60 + current.minute
    return start <= minutes < end


def _hhmm(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)
