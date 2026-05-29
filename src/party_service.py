from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from models import PlaybackState, QueueItem
from persistence import QueueStore

if TYPE_CHECKING:
    from spotify_client import SpotifyClient

logger = logging.getLogger(__name__)

TRACK_END_THRESHOLD_MS = 5000


class PartyService:
    def __init__(self, spotify: SpotifyClient, store: QueueStore):
        self._spotify = spotify
        self._store = store
        self._version: int = 0
        self._last_skip_version: int = 0
        self._beaver_enabled: bool = True

    @property
    def spotify(self) -> SpotifyClient:
        return self._spotify

    @property
    def version(self) -> int:
        return self._version

    @property
    def has_session(self) -> bool:
        return self._store.has_session

    @property
    def session_name(self) -> str | None:
        return self._store.session_name

    @property
    def device_id(self) -> str | None:
        return self._store.device_id

    @property
    def playback_state(self) -> PlaybackState:
        return self._store.playback_state

    @property
    def last_skip_version(self) -> int:
        return self._last_skip_version

    @property
    def beaver_enabled(self) -> bool:
        return self._beaver_enabled

    def set_beaver_enabled(self, enabled: bool) -> None:
        self._beaver_enabled = enabled

    def start_session(self, name: str, device_id: str) -> None:
        self._store.start_session(name, device_id)
        self._bump_version()

    def search_songs(self, query: str) -> list[QueueItem]:
        tracks = self._spotify.search_tracks(query)
        return [QueueItem.from_spotify_track(t, requester="") for t in tracks]

    def add_to_queue(self, item: QueueItem, top: bool = False) -> None:
        self._store.add_to_queue(item, top=top)
        self._bump_version()

    def remove_from_queue(self, track_uri: str) -> None:
        self._store.remove_from_queue(track_uri)
        self._bump_version()

    def move_to_top(self, track_uri: str) -> None:
        self._store.move_to_top(track_uri)
        self._bump_version()

    def get_queue(self) -> list[QueueItem]:
        return list(self._store.queue)

    def get_currently_playing(self) -> QueueItem | None:
        return self._store.currently_playing

    def play_next(self) -> None:
        item = self._store.pop_next()
        if item is None:
            return
        self._spotify.play_track(item.track_uri, device_id=self._store.device_id)
        self._store.set_currently_playing(item, PlaybackState.PLAYING)
        self._last_skip_version += 1
        self._bump_version()

    def pause(self) -> None:
        self._spotify.pause(device_id=self._store.device_id)
        self._store.set_playback_state(PlaybackState.PAUSED)
        self._bump_version()

    def resume(self) -> None:
        self._spotify.resume(device_id=self._store.device_id)
        self._store.set_playback_state(PlaybackState.PLAYING)
        self._bump_version()

    def set_device(self, device_id: str) -> None:
        self._store.set_device(device_id)
        self._bump_version()

    def update_requester(self, track_uri: str, requester: str) -> None:
        self._store.update_requester(track_uri, requester)
        self._bump_version()

    def get_known_requesters(self) -> list[str]:
        return self._store.get_known_requesters()

    def get_devices(self) -> list[dict]:
        return self._spotify.get_devices()

    def poll_playback(self) -> None:
        if self._store.playback_state == PlaybackState.IDLE:
            return

        state = self._spotify.get_playback_state()
        if state is None:
            if self._store.currently_playing is not None:
                self._store.clear_currently_playing()
                self._bump_version()
            return

        is_playing = state.get("is_playing", False)
        item = state.get("item")
        progress = state.get("progress_ms", 0)
        duration = item.get("duration_ms", 0) if item else 0

        track_ended = not is_playing and duration > 0 and (duration - progress) < TRACK_END_THRESHOLD_MS

        if track_ended:
            next_item = self._store.pop_next()
            if next_item:
                self._spotify.play_track(next_item.track_uri, device_id=self._store.device_id)
                self._store.set_currently_playing(next_item, PlaybackState.PLAYING)
            else:
                self._store.clear_currently_playing()
            self._bump_version()

    def _bump_version(self) -> None:
        self._version += 1
