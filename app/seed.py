from __future__ import annotations

from app.clock import iso
from app.policy import default_policy
from app.store import empty_state, get_store


def demo_start_state() -> dict:
    """Start of the video: two doors, no policy saved, locks open, empty inbox."""
    state = empty_state()
    state["disclaimer"] = "We do not control the device."
    return state


def seeded_week_state() -> dict:
    """A lived-in week so a live URL is not an empty house."""
    state = empty_state()
    child = state["child"]
    state["policy"] = default_policy(child)
    state["locks"] = {
        "screen_time_on": True,
        "ask_to_install": True,
        "youtube_supervised": True,
        "roblox_pin": False,
        "downtime_school_hours": True,
        "locks_claimed_on": "2026-09-01",
    }
    state["snapshots"] = [
        {
            "id": "snap_prev",
            "kid": "aarav",
            "date": "2026-08-30",
            "kind": "saturday",
            "apps": [
                {"name": "YouTube", "minutes": 40},
                {"name": "Google Classroom", "minutes": 25},
                {"name": "WhatsApp", "minutes": 15},
            ],
            "source": "human_paste",
            "new_unapproved": [],
            "note": "Human-pasted snapshot. Not a vendor feed.",
        }
    ]
    state["decisions"] = [
        {
            "id": "dec_maps",
            "kind": "extra_time",
            "subject": "Maps",
            "status": "allowed",
            "reason": "Sports-phone preset.",
            "at": "2026-09-02T18:10:00+05:30",
        }
    ]
    state["events"] = [
        {
            "id": "evt_ptm",
            "title": "PTM with class teacher",
            "notes": "Bring Aarav’s last two tests.",
            "location": "School block B",
            "date": "2026-09-11",
            "end_date": None,
            "all_day": False,
            "start_time": "18:00",
            "end_time": "18:40",
            "calendar": "important",
            "who": "parent",
            "repeat": "none",
            "repeat_until": None,
            "important": True,
            "created_by": "parent",
            "source": "user",
            "created_at": iso(),
        },
        {
            "id": "evt_cricket",
            "title": "Cricket practice",
            "notes": "Maps and Phone extra time is allowed.",
            "location": "Club ground",
            "date": "2026-09-08",
            "end_date": None,
            "all_day": False,
            "start_time": "16:30",
            "end_time": "18:00",
            "calendar": "sports",
            "who": "child",
            "repeat": "weekly",
            "repeat_until": "2026-11-30",
            "important": False,
            "created_by": "parent",
            "source": "user",
            "created_at": iso(),
        },
        {
            "id": "evt_maths",
            "title": "Maths unit test",
            "notes": "Linear equations chapter.",
            "location": "Classroom",
            "date": "2026-09-18",
            "end_date": None,
            "all_day": False,
            "start_time": "09:30",
            "end_time": "10:30",
            "calendar": "school",
            "who": "child",
            "repeat": "none",
            "repeat_until": None,
            "important": True,
            "created_by": "parent",
            "source": "user",
            "created_at": iso(),
        },
        {
            "id": "evt_grandma",
            "title": "Grandma’s house",
            "notes": "Leave phones in the bag during dinner.",
            "location": "Jayanagar",
            "date": "2026-09-20",
            "end_date": None,
            "all_day": True,
            "start_time": None,
            "end_time": None,
            "calendar": "family",
            "who": "family",
            "repeat": "none",
            "repeat_until": None,
            "important": False,
            "created_by": "child",
            "source": "user",
            "created_at": iso(),
        },
    ]
    state["todos"] = [
        {
            "id": "todo_hw",
            "date": "2026-09-09",
            "title": "Finish maths worksheet before YouTube",
            "done": False,
            "by": "parent",
            "created_at": iso(),
        },
        {
            "id": "todo_kit",
            "date": "2026-09-10",
            "title": "Pack cricket kit",
            "done": False,
            "by": "child",
            "created_at": iso(),
        },
    ]
    state["agent_log"] = [
        {
            "at": iso(),
            "agent": "setup_coach",
            "event": "seed",
            "summary": "Seeded a quiet previous Saturday so the desk is not empty.",
        }
    ]
    return state


def seed(kind: str = "demo") -> dict:
    data = seeded_week_state() if kind == "week" else demo_start_state()
    return get_store().replace(data)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--week", action="store_true")
    args = parser.parse_args()
    state = seed("week" if args.week else "demo")
    print(f"Seeded family {state['family_id']} ({'week' if args.week else 'demo start'})")
