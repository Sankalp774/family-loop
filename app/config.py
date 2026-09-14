from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

DATA_PATH = Path(os.environ.get("FAMILY_LOOP_DATA", ROOT / "data" / "family.json"))
SESSIONS_DIR = Path(os.environ.get("FAMILY_LOOP_SESSIONS", ROOT / "data" / "sessions"))
MODEL_MODE = os.environ.get("FAMILY_LOOP_MODEL", "lmstudio").strip().lower()
LMSTUDIO_MODEL = os.environ.get("LMSTUDIO_MODEL", "").strip()


def lmstudio_base() -> str:
    raw = os.environ.get("LMSTUDIO_BASE_URL", "http://192.168.31.64:1234").rstrip("/")
    if raw.endswith("/v1"):
        return raw
    return raw + "/v1"


def current_model_mode() -> str:
    raw = os.environ.get("FAMILY_LOOP_MODEL", MODEL_MODE).strip().lower()
    if raw in {"mock", "demo", "scripted"}:
        return "scripted"
    if raw in {"lmstudio", "lm-studio", "local"}:
        return "lmstudio"
    if raw in {"bedrock", "aws", "sonnet"}:
        return "bedrock"
    return raw or "scripted"


def set_model_mode(mode: str) -> str:
    global MODEL_MODE
    key = (mode or "scripted").strip().lower()
    if key in {"mock", "demo", "scripted"}:
        key = "scripted"
    elif key in {"lmstudio", "lm-studio", "local"}:
        key = "lmstudio"
    elif key in {"bedrock", "aws", "sonnet"}:
        key = "bedrock"
    else:
        raise ValueError("mode must be bedrock or lmstudio")
    MODEL_MODE = key
    os.environ["FAMILY_LOOP_MODEL"] = "mock" if key == "scripted" else key
    return key
AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-6"
)
SECRET = os.environ.get("FAMILY_LOOP_SECRET", "family-loop-demo-secret")
TZ_NAME = os.environ.get("FAMILY_LOOP_TZ", "Asia/Kolkata")

# Demo logins — judges should see two doors, not a shared admin.
USERS = {
    "meera@familyloop.demo": {
        "password": "parent",
        "role": "parent",
        "name": "Meera",
        "kid": "aarav",
    },
    "aarav@familyloop.demo": {
        "password": "aarav",
        "role": "child",
        "name": "Aarav",
        "kid": "aarav",
    },
}

LOCK_ITEMS = [
    {
        "key": "screen_time_on",
        "label": "Screen Time / Digital Wellbeing is on",
        "hint": "The phone OS is the lock. We only read what a human pastes.",
    },
    {
        "key": "ask_to_install",
        "label": "Ask to install is on",
        "hint": "iOS Screen Time or Family Link install gate.",
    },
    {
        "key": "youtube_supervised",
        "label": "YouTube is on a supervised account",
        "hint": "Not the same as ‘we locked YouTube’.",
    },
    {
        "key": "roblox_pin",
        "label": "Roblox PIN / chat restrictions are set",
        "hint": "We never read Roblox DMs.",
    },
    {
        "key": "downtime_school_hours",
        "label": "Downtime covers school hours",
        "hint": "OS downtime. Family Loop will not ping during it.",
    },
]

SOCIAL_SUBJECTS = {
    "reddit",
    "discord",
    "instagram",
    "tiktok",
    "snapchat",
    "x",
    "twitter",
    "facebook",
    "whatsapp",
    "telegram",
    "beReal",
    "bereal",
    "youtube",
}

ASK_FIRST_CHOICES = [
    {"key": "new_app", "label": "New apps", "hint": "Anything not already on the allowed list."},
    {"key": "new_contact", "label": "New in-app friends", "hint": "A name they type. We never scrape chats."},
    {"key": "social", "label": "Social apps", "hint": "Reddit, Discord, Instagram, and the like."},
    {"key": "in_app_purchase", "label": "Anything that costs money", "hint": "Robux, gift cards, in-app buys."},
    {"key": "extra_time_over_cap", "label": "Extra time over the cap", "hint": "More minutes than the daily limit."},
]

HARD_NO_CHOICES = [
    {"key": "gambling", "label": "Gambling", "hint": "Denied without asking."},
    {"key": "dating", "label": "Dating apps", "hint": "Denied without asking."},
    {
        "key": "unsupervised_late_night_youtube",
        "label": "YouTube late at night without you",
        "hint": "After bedtime, no unsupervised YouTube.",
    },
]

KIND_CHOICES = [
    {"key": "visit_site", "label": "Visit a site"},
    {"key": "install_app", "label": "Install an app"},
    {"key": "extra_time", "label": "Extra time"},
    {"key": "new_contact", "label": "New in-app friend"},
]

PARENT_NOTE_DEFAULT = (
    "Sports-phone preset: Maps and Phone extra time during practice is allowed. "
    "YouTube extra time waits until after homework hours (17:00)."
)

PURCHASE_HINTS = (
    "buy",
    "purchase",
    "robux",
    "v-bucks",
    "vbucks",
    "in-app",
    "iap",
    "gift card",
    "rupees",
    "₹",
    "$",
)
