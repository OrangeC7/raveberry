"""This module handles realtime communication via websockets."""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse

from core import user_manager

logger = logging.getLogger(__name__)

STATE_GROUP = "state"
WS_SEND_TIMEOUT_SECONDS = 5.0
WS_CLOSE_TIMEOUT_SECONDS = 1.0


def send_state(_state: Dict[str, Any]) -> None:
    """Notify clients that state changed.

    Do not send the full state through the websocket. Full state can become large
    after songs are added, and slow/broken websocket clients can stall the UI.
    Clients receive this tiny invalidation message and fetch state over HTTP.
    """
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    try:
        async_to_sync(channel_layer.group_send)(
            STATE_GROUP,
            {
                "type": "state_update",
                "state": {"type": "state_dirty"},
            },
        )
    except Exception:  # pylint: disable=broad-except
        logger.warning("WS STATE DIRTY BROADCAST FAILED", exc_info=True)


def get_state(_request: WSGIRequest, module) -> JsonResponse:
    """Calls the get_state function of the given module and returns its result."""
    state = module.state_dict()
    return JsonResponse(state)


class StateConsumer(AsyncWebsocketConsumer):
    """Handles connections with websocket clients."""

    async def connect(self) -> None:
        self.client_ip = user_manager.get_client_ip_from_scope(self.scope)
        self._joined_state_group = False

        try:
            banned = False
            if self.client_ip:
                banned = await database_sync_to_async(user_manager.is_banned_ip)(
                    self.client_ip
                )

            if banned:
                logger.info(
                    "WS REJECT %s [ip=%s]",
                    self.scope.get("path", ""),
                    self.client_ip,
                )
                await self._safe_close(code=4003)
                raise StopConsumer()

            logger.info(
                "WS CONNECT %s [ip=%s]",
                self.scope.get("path", ""),
                self.client_ip or "",
            )

            await self.channel_layer.group_add(STATE_GROUP, self.channel_name)
            self._joined_state_group = True
            await self.accept()
        except StopConsumer:
            raise
        except Exception:  # pylint: disable=broad-except
            logger.warning(
                "WS CONNECT FAILED %s [ip=%s]",
                self.scope.get("path", ""),
                self.client_ip or "",
                exc_info=True,
            )
            await self._safe_close()
            raise StopConsumer()

    async def disconnect(self, code: int) -> None:
        logger.info(
            "WS DISCONNECT %s [ip=%s code=%s]",
            self.scope.get("path", ""),
            getattr(self, "client_ip", "") or "",
            code,
        )

        if getattr(self, "_joined_state_group", False):
            try:
                await self.channel_layer.group_discard(
                    STATE_GROUP,
                    self.channel_name,
                )
            except Exception:  # pylint: disable=broad-except
                logger.warning(
                    "WS GROUP DISCARD FAILED %s [ip=%s code=%s]",
                    self.scope.get("path", ""),
                    getattr(self, "client_ip", "") or "",
                    code,
                    exc_info=True,
                )
            finally:
                self._joined_state_group = False

    async def receive(
        self,
        text_data: Optional[str] = None,
        bytes_data: Optional[bytes] = None,
    ) -> None:
        return

    async def state_update(self, event: Dict[str, Any]) -> None:
        """Receives a state-change message and sends it to the websocket."""
        try:
            await asyncio.wait_for(
                self.send(text_data=json.dumps(event["state"])),
                timeout=WS_SEND_TIMEOUT_SECONDS,
            )
        except Exception:  # pylint: disable=broad-except
            logger.warning(
                "WS SEND FAILED; dropping websocket %s [ip=%s]",
                self.scope.get("path", ""),
                getattr(self, "client_ip", "") or "",
                exc_info=True,
            )
            await self._safe_close(code=1011)
            raise StopConsumer()

    async def _safe_close(self, code: Optional[int] = None) -> None:
        try:
            if code is None:
                await asyncio.wait_for(self.close(), timeout=WS_CLOSE_TIMEOUT_SECONDS)
            else:
                await asyncio.wait_for(
                    self.close(code=code),
                    timeout=WS_CLOSE_TIMEOUT_SECONDS,
                )
        except Exception:  # pylint: disable=broad-except
            pass
