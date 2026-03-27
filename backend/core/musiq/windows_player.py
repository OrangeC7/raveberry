"""Windows native playback backend using python-vlc."""

from __future__ import annotations

import time
from typing import Optional

from core import redis
from core.musiq import player
from core.musiq.playback import PlaybackError

try:
    import vlc  # python-vlc
except ImportError:  # handled at runtime
    vlc = None


_INSTANCE: Optional["WindowsPlayer"] = None


def _get_instance() -> "WindowsPlayer":
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = WindowsPlayer()
    return _INSTANCE


class WindowsPlayer(player.Player):
    def __init__(self) -> None:
        if vlc is None:
            raise PlaybackError("python-vlc is not installed")

        self.instance = vlc.Instance()
        self.media_player = self.instance.media_player_new()

    def _set_media(self, uri: str) -> None:
        media = self.instance.media_new(uri)
        self.media_player.set_media(media)

    def start_song(self, song, catch_up: Optional[float]) -> None:
        uri = song.internal_url or song.stream_url or song.external_url
        if not uri:
            raise PlaybackError("No playable URI")

        self._set_media(uri)

        if self.media_player.play() == -1:
            raise PlaybackError("VLC failed to start playback")

        # give VLC a moment to start
        for _ in range(20):
            state = self.media_player.get_state()
            if state not in (vlc.State.NothingSpecial, vlc.State.Opening):
                break
            time.sleep(0.1)

        if catch_up is not None and catch_up >= 0:
            self.media_player.set_time(int(catch_up))

        if redis.get("paused"):
            self.media_player.pause()

    def should_stop_waiting(self, previous_error: bool) -> bool:
        state = self.media_player.get_state()
        return state in (
            vlc.State.Ended,
            vlc.State.Stopped,
            vlc.State.Error,
        )

    def play_alarm(self, interrupt: bool, alarm_path: str) -> None:
        if interrupt:
            self.media_player.stop()
        self._set_media("file:///" + alarm_path.replace("\\", "/"))
        if self.media_player.play() == -1:
            raise PlaybackError("VLC failed to play alarm")

    def play_backup_stream(self) -> None:
        # current song already stores playable URLs; backup stream support can be added later
        pass

    @staticmethod
    def restart() -> None:
        inst = _get_instance()
        inst.media_player.set_time(0)
        inst.media_player.play()

    @staticmethod
    def seek_backward(seek_distance: float) -> None:
        inst = _get_instance()
        pos = inst.media_player.get_time()
        inst.media_player.set_time(max(0, pos - int(seek_distance * 1000)))

    @staticmethod
    def play() -> None:
        _get_instance().media_player.play()

    @staticmethod
    def pause() -> None:
        _get_instance().media_player.pause()

    @staticmethod
    def seek_forward(seek_distance: float) -> None:
        inst = _get_instance()
        pos = inst.media_player.get_time()
        inst.media_player.set_time(max(0, pos + int(seek_distance * 1000)))

    @staticmethod
    def skip() -> None:
        _get_instance().media_player.stop()

    @staticmethod
    def set_volume(volume) -> None:
        _get_instance().media_player.audio_set_volume(round(volume * 100))
