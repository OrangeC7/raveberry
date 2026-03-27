"""Runtime-only public site mode for FURATIC."""
from core import redis

EVENT_MODE = "event"
AFTER_HOURS_MODE = "afterhours"
VALID_MODES = {EVENT_MODE, AFTER_HOURS_MODE}


def get_mode() -> str:
    mode = str(redis.get("site_mode"))
    return mode if mode in VALID_MODES else EVENT_MODE


def set_mode(mode: str) -> str:
    normalized = AFTER_HOURS_MODE if mode == AFTER_HOURS_MODE else EVENT_MODE
    redis.put("site_mode", normalized)
    return normalized


def is_afterhours() -> bool:
    return get_mode() == AFTER_HOURS_MODE
