"""Lightweight Redis-backed audit log for moderator and user actions."""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from django.core.handlers.wsgi import WSGIRequest

from core import redis, user_manager

AUDIT_LOG_KEY = "audit-log:v1"
AUDIT_LOG_LIMIT = 250
AUDIT_LOG_TTL_SECONDS = 7 * 24 * 60 * 60


def _actor_label(request: Optional[WSGIRequest]) -> str:
    if request is None:
        return "system"

    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        username = getattr(user, "get_username", lambda: "")() or getattr(user, "username", "")
        if username:
            return username

    session = getattr(request, "session", None)
    session_key = getattr(session, "session_key", None)
    if session_key:
        return f"session:{session_key[:8]}"

    return "anonymous"


def _actor_role(request: Optional[WSGIRequest]) -> str:
    if request is None:
        return "system"

    user = getattr(request, "user", None)
    if user_manager.is_admin(user):
        return "admin"
    if user_manager.is_moderator(user):
        return "moderator"
    return "user"


def append(
    action: str,
    *,
    request: Optional[WSGIRequest] = None,
    target: str = "",
    song_key: Optional[int] = None,
    song_title: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    entry = {
        "ts": time.time(),
        "action": action,
        "actor": _actor_label(request),
        "actorRole": _actor_role(request),
        "ip": user_manager.get_client_ip(request) if request is not None else "",
        "target": target,
        "songKey": song_key,
        "songTitle": song_title,
        "metadata": metadata or {},
    }

    pipe = redis.connection.pipeline()
    pipe.lpush(AUDIT_LOG_KEY, json.dumps(entry))
    pipe.ltrim(AUDIT_LOG_KEY, 0, AUDIT_LOG_LIMIT - 1)
    pipe.expire(AUDIT_LOG_KEY, AUDIT_LOG_TTL_SECONDS)
    pipe.execute()


def get_recent(limit: int = 120) -> List[Dict[str, Any]]:
    raw_entries = redis.connection.lrange(AUDIT_LOG_KEY, 0, max(0, limit - 1))
    entries: List[Dict[str, Any]] = []
    for raw in raw_entries:
        try:
            entries.append(json.loads(raw))
        except (TypeError, json.JSONDecodeError):
            continue
    return entries
