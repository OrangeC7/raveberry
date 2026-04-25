"""Websocket routes.

State websockets are disabled. The frontend uses HTTP polling for state.
"""

WEBSOCKET_URLPATTERNS = []

# Backward-compatible alias in case any other code imports the old/lowercase name.
websocket_urlpatterns = WEBSOCKET_URLPATTERNS
