from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from spotipy.exceptions import SpotifyException

from adem_mode import AdemMode
from models import PartyEvent, PartyEventType, PlaybackInfo, PlaybackState, QueueItem
from persistence import QueueStore

if TYPE_CHECKING:
    from spotify_client import SpotifyClient

logger = logging.getLogger(__name__)

TRACK_END_THRESHOLD_MS = 5000
PLAYBACK_SETTLE_SECONDS = 5


class PartyService:
    MAX_EVENTS = 50

    def __init__(self, spotify: SpotifyClient, store: QueueStore):
        self._spotify = spotify
        self._store = store
        self._adem = AdemMode(store)
        self._version: int = 0
        self._events: list[PartyEvent] = []
        self._beaver_enabled: bool = False
        self._show_qr_code: bool = False
        self._playback_commanded_at: float = 0.0

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

    def get_events_since(self, since_version: int) -> list[PartyEvent]:
        return [e for e in self._events if e.version > since_version]

    def _emit(
        self, kind: PartyEventType, track_uri: str, *, is_priority: bool = False
    ) -> None:
        self._events.append(
            PartyEvent(
                kind=kind,
                track_uri=track_uri,
                version=self._version,
                is_priority=is_priority,
            )
        )
        if len(self._events) > self.MAX_EVENTS:
            self._events = self._events[-self.MAX_EVENTS :]

    @property
    def beaver_enabled(self) -> bool:
        return self._beaver_enabled

    @property
    def show_qr_code(self) -> bool:
        return self._show_qr_code

    @property
    def adem_mode_active(self) -> bool:
        return self._adem.active

    def is_authenticated(self) -> bool:
        return self._spotify.is_authenticated()

    def get_auth_url(self) -> str:
        return self._spotify.get_auth_url()

    def handle_auth_callback(self, code: str) -> None:
        self._spotify.handle_auth_callback(code)

    def set_beaver_enabled(self, enabled: bool) -> None:
        self._beaver_enabled = enabled

    def set_show_qr_code(self, enabled: bool) -> None:
        self._show_qr_code = enabled
        self._bump_version()

    def start_session(self, name: str, device_id: str, adem_mode: bool = False) -> None:
        self._store.start_session(name, device_id)
        if adem_mode:
            self._adem.activate()
        self._bump_version()

    def fill_benchmark_queue(self, items: list[QueueItem]) -> None:
        self._store.clear_queue()
        for item in items:
            self._store.add_to_queue(item)
        self._bump_version()

    def search_songs(self, query: str) -> list[QueueItem]:
        return self._spotify.search_tracks(query)

    def add_to_queue(self, item: QueueItem, top: bool = False) -> None:
        self._adem.on_user_add()
        self._store.add_to_queue(item, top=top)
        self._bump_version()
        self._emit(PartyEventType.ADDED, item.track_uri, is_priority=top)

    def remove_from_queue(self, uid: str) -> None:
        self._store.remove_from_queue(uid)
        self._bump_version()

    def clear_queue(self) -> None:
        self._store.clear_queue()
        self._bump_version()

    def move_to_top(self, uid: str) -> None:
        self._store.move_to_top(uid)
        moved = next((q for q in self._store.queue if q.uid == uid), None)
        self._bump_version()
        if moved:
            self._emit(PartyEventType.MOVED_TO_TOP, moved.track_uri)

    def move_up(self, uid: str) -> None:
        self._store.move_up(uid)
        self._bump_version()

    def move_down(self, uid: str) -> None:
        self._store.move_down(uid)
        self._bump_version()

    def get_queue(self) -> list[QueueItem]:
        return list(self._store.queue)

    def get_currently_playing(self) -> QueueItem | None:
        return self._store.currently_playing

    def play_next(self) -> None:
        self._refill_adem_if_needed()
        item = self._store.pop_next()
        if item is None:
            return
        self._spotify.play_track(item.track_uri, device_id=self._store.device_id)
        self._playback_commanded_at = time.monotonic()
        self._store.set_currently_playing(item, PlaybackState.PLAYING)
        self._bump_version()
        self._emit(PartyEventType.SKIPPED, item.track_uri)

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

    def update_requester(self, uid: str, requester: str) -> None:
        self._store.update_requester(uid, requester)
        self._bump_version()

    def get_known_requesters(self) -> list[str]:
        return self._store.get_known_requesters()

    def get_devices(self) -> list[dict]:
        return self._spotify.get_devices()

    def _is_our_track(self, info: PlaybackInfo) -> bool:
        current = self._store.currently_playing
        if current is None or info.track_uri is None:
            return False
        return info.track_uri == current.track_uri

    def _in_settle_period(self) -> bool:
        return (
            time.monotonic() - self._playback_commanded_at
        ) < PLAYBACK_SETTLE_SECONDS

    def poll_playback(self) -> None:
        if self._store.playback_state == PlaybackState.IDLE:
            return

        info = self._spotify.get_playback_state()
        if info is None:
            if (
                self._store.currently_playing is not None
                and not self._in_settle_period()
            ):
                logger.info("Playback stopped externally, advancing queue")
                self._advance_queue()
            return

        if not self._is_our_track(info):
            if self._in_settle_period():
                return
            logger.info("Our track no longer on Spotify, advancing queue")
            self._advance_queue()
            return

        track_ended = (
            not info.is_playing
            and info.duration_ms > 0
            and (info.duration_ms - info.progress_ms) < TRACK_END_THRESHOLD_MS
        )

        if track_ended:
            self._advance_queue()
            return

        if info.is_playing and self._store.playback_state == PlaybackState.PAUSED:
            logger.info("Playback resumed externally")
            self._store.set_playback_state(PlaybackState.PLAYING)
            self._bump_version()
        elif (
            not info.is_playing and self._store.playback_state == PlaybackState.PLAYING
        ):
            logger.info("Playback paused externally")
            self._store.set_playback_state(PlaybackState.PAUSED)
            self._bump_version()

        self._refill_adem_if_needed()

    def _refill_adem_if_needed(self) -> None:
        if self._adem.refill_if_needed():
            self._bump_version()

    def _advance_queue(self) -> None:
        self._refill_adem_if_needed()
        next_item = self._store.pop_next()
        if next_item:
            try:
                self._spotify.play_track(
                    next_item.track_uri, device_id=self._store.device_id
                )
                self._playback_commanded_at = time.monotonic()
                self._store.set_currently_playing(next_item, PlaybackState.PLAYING)
            except SpotifyException:
                logger.warning("Failed to start next track, re-queuing")
                self._store.add_to_queue(next_item, top=True)
                self._store.clear_currently_playing()
        else:
            self._store.clear_currently_playing()
        self._bump_version()

    def _bump_version(self) -> None:
        self._version += 1
