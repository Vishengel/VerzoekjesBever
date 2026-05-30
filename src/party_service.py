from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from spotipy.exceptions import SpotifyException

from models import PartyEvent, PartyEventType, PlaybackState, QueueItem
from persistence import QueueStore

if TYPE_CHECKING:
    from spotify_client import SpotifyClient

logger = logging.getLogger(__name__)

TRACK_END_THRESHOLD_MS = 5000

DEMO_SONG = QueueItem(
    track_name="Ademnood",
    artist="Linda Roos & Jessica",
    album_art_url="https://i.scdn.co/image/ab67616d0000b273eadf932fba8bf38eba3947a1",
    track_uri="spotify:track:5ljuGR6Fv7B2mviKflDoE4",
    requester="🦫",
)
DEMO_QUEUE_SIZE = 50


class PartyService:
    MAX_EVENTS = 50

    def __init__(self, spotify: SpotifyClient, store: QueueStore):
        self._spotify = spotify
        self._store = store
        self._version: int = 0
        self._events: list[PartyEvent] = []
        self._beaver_enabled: bool = False
        self._show_qr_code: bool = False

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
    def demo_queue_active(self) -> bool:
        return self._store.demo_queue_active

    def set_beaver_enabled(self, enabled: bool) -> None:
        self._beaver_enabled = enabled

    def set_show_qr_code(self, enabled: bool) -> None:
        self._show_qr_code = enabled
        self._bump_version()

    def start_session(self, name: str, device_id: str, demo: bool = False) -> None:
        self._store.start_session(name, device_id)
        if demo:
            self.fill_demo_queue()
        self._bump_version()

    def fill_demo_queue(self) -> None:
        for _ in range(DEMO_QUEUE_SIZE):
            self._store.add_to_queue(DEMO_SONG)
        self._store.set_demo_queue_active(True)

    def fill_benchmark_queue(self, items: list[QueueItem]) -> None:
        self._store.clear_queue()
        for item in items:
            self._store.add_to_queue(item)
        self._store.set_demo_queue_active(True)
        self._bump_version()

    def search_songs(self, query: str) -> list[QueueItem]:
        tracks = self._spotify.search_tracks(query)
        return [QueueItem.from_spotify_track(t, requester="") for t in tracks]

    def add_to_queue(self, item: QueueItem, top: bool = False) -> None:
        if self._store.demo_queue_active:
            self._store.set_demo_queue_active(False)
            self._store.clear_queue()
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
        item = self._store.pop_next()
        if item is None:
            return
        self._spotify.play_track(item.track_uri, device_id=self._store.device_id)
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

    def poll_playback(self) -> None:
        if self._store.playback_state == PlaybackState.IDLE:
            return

        state = self._spotify.get_playback_state()
        if state is None:
            if self._store.currently_playing is not None:
                logger.info("Playback stopped externally, advancing queue")
                self._advance_queue()
            return

        is_playing = state.get("is_playing", False)
        item = state.get("item")
        progress = state.get("progress_ms", 0)
        duration = item.get("duration_ms", 0) if item else 0

        track_ended = (
            not is_playing
            and duration > 0
            and (duration - progress) < TRACK_END_THRESHOLD_MS
        )

        if track_ended:
            self._advance_queue()
            return

        if is_playing and self._store.playback_state == PlaybackState.PAUSED:
            logger.info("Playback resumed externally")
            self._store.set_playback_state(PlaybackState.PLAYING)
            self._bump_version()
        elif not is_playing and self._store.playback_state == PlaybackState.PLAYING:
            logger.info("Playback paused externally")
            self._store.set_playback_state(PlaybackState.PAUSED)
            self._bump_version()

    def _advance_queue(self) -> None:
        next_item = self._store.pop_next()
        if next_item:
            try:
                self._spotify.play_track(
                    next_item.track_uri, device_id=self._store.device_id
                )
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
