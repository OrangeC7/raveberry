"""This module handles state responses.

The websocket state channel is intentionally disabled for this deployment path.
The frontend uses HTTP polling instead. This avoids websocket reconnect storms
from taking down ordinary HTTP routes.
"""

import logging
from typing import Any, Dict

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def send_state(_state: Dict[str, Any]) -> None:
    """State changes are picked up by frontend HTTP polling.

    This must stay cheap and non-blocking because it is called from song add,
    download completion, voting, playback changes, and settings changes.
    """


def get_state(_request: WSGIRequest, module) -> JsonResponse:
    """Calls the get_state function of the given module and returns its result."""
    state = module.state_dict()
    return JsonResponse(state)
