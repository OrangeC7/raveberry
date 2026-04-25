"""This module handles state responses.

Frontend state updates use HTTP polling. The websocket route is kept as a
no-op compatibility endpoint so cached/old clients that still connect to
/state/ do not create Channels routing errors or reconnect storms.
"""

import logging
from typing import Any, Dict, Optional

from channels.generic.websocket import AsyncWebsocketConsumer
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


class StateConsumer(AsyncWebsocketConsumer):
    """Compatibility websocket for cached clients.

    Do not join groups. Do not send state. Do not close immediately. Keeping the
    socket open prevents old ReconnectingWebSocket clients from hammering the
    server with reconnect attempts.
    """

    async def connect(self) -> None:
        await self.accept()

    async def disconnect(self, code: int) -> None:
        return

    async def receive(
        self,
        text_data: Optional[str] = None,
        bytes_data: Optional[bytes] = None,
    ) -> None:
        return
