"""This module handles realtime communication via websockets."""
import json
from typing import Any, Dict

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from channels.layers import get_channel_layer
from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse
from core import user_manager
import logging
from core import user_manager

logger = logging.getLogger(__name__)

def send_state(state: Dict[str, Any]) -> None:
    """Sends the given dictionary as a state update to all connected clients."""
    data = {"type": "state_update", "state": state}
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)("state", data)


def get_state(_request: WSGIRequest, module) -> JsonResponse:
    """Calls the get_state function of the given module and returns its result."""
    state = module.state_dict()
    return JsonResponse(state)


class StateConsumer(WebsocketConsumer):
    """Handles connections with websocket clients."""

    def connect(self) -> None:
        self.client_ip = user_manager.get_client_ip_from_scope(self.scope)

        if self.client_ip and user_manager.is_banned_ip(self.client_ip):
            logger.info(
                "WS REJECT %s [ip=%s]",
                self.scope.get("path", ""),
                self.client_ip,
            )
            self.close(code=4003)
            return

        logger.info(
            "WS CONNECT %s [ip=%s]",
            self.scope.get("path", ""),
            self.client_ip or "",
        )
        async_to_sync(self.channel_layer.group_add)("state", self.channel_name)
        self.accept()

    def disconnect(self, code: int) -> None:
        logger.info(
            "WS DISCONNECT %s [ip=%s code=%s]",
            self.scope.get("path", ""),
            getattr(self, "client_ip", "") or "",
            code,
        )
        async_to_sync(self.channel_layer.group_discard)("state", self.channel_name)

    def receive(self, text_data: str = None, bytes_data: bytes = None) -> None:
        pass

    def state_update(self, event: Dict[str, Any]):
        """Receives a message from the room group and sends it back to the websocket."""
        self.send(text_data=json.dumps(event["state"]))

    def disconnect(self, code: int) -> None:
        async_to_sync(self.channel_layer.group_discard)("state", self.channel_name)

    def receive(self, text_data: str = None, bytes_data: bytes = None) -> None:
        pass

    def state_update(self, event: Dict[str, Any]):
        """Receives a message from the room group and sends it back to the websocket."""
        self.send(text_data=json.dumps(event["state"]))
