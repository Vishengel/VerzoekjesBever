from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import TYPE_CHECKING

from models import QueueItem
from persistence import RequesterMap

if TYPE_CHECKING:
    from spotify_client import SpotifyClient


class PartyService:
    def __init__(self, spotify: SpotifyClient, requester_map: RequesterMap):
        self._spotify = spotify
        self._requester_map = requester_map
        self._queue: list[QueueItem] = []
        self._currently_playing: QueueItem | None = None
        self._subscribers: list[Callable] = []
        self._version: int = 0
        self.playlist_id: str | None = None

    @property
    def version(self) -> int:
        return self._version

    def start_session(self, playlist_id: str | None, playlist_name: str | None = None) -> None:
        if playlist_id is None:
            name = playlist_name or f"VerzoekjesBever — {date.today().strftime('%d %B %Y')}"
            result = self._spotify.create_playlist(name)
            self.playlist_id = result["id"]
        else:
            self.playlist_id = playlist_id
            self._load_queue_from_spotify()

    def search_songs(self, query: str) -> list[QueueItem]:
        tracks = self._spotify.search_tracks(query)
        return [QueueItem.from_spotify_track(t, requester="") for t in tracks]

    def add_song(self, track: dict, requester: str, top: bool = False) -> None:
        item = QueueItem.from_spotify_track(track, requester=requester)
        position = 0 if top else None
        self._spotify.add_track_to_playlist(self.playlist_id, item.track_uri, position=position)
        if top:
            self._queue.insert(0, item)
        else:
            self._queue.append(item)
        self._requester_map.add(item.track_uri, requester)
        self._bump_version()

    def remove_currently_playing(self) -> None:
        if self._currently_playing is None:
            return
        self._spotify.remove_track_from_playlist(self.playlist_id, self._currently_playing.track_uri)
        self._requester_map.remove(self._currently_playing.track_uri)
        self._currently_playing = None
        self._bump_version()

    def get_queue(self) -> list[QueueItem]:
        return list(self._queue)

    def get_currently_playing(self) -> QueueItem | None:
        return self._currently_playing

    def subscribe(self, callback: Callable) -> None:
        self._subscribers.append(callback)

    def poll_currently_playing(self) -> None:
        track = self._spotify.get_currently_playing_track()
        if track is None:
            if self._currently_playing is not None:
                self._currently_playing = None
                self._bump_version()
            return

        new_uri = track["uri"]
        if self._currently_playing and self._currently_playing.track_uri == new_uri:
            return

        requesters = self._requester_map.get(new_uri)
        requester = requesters[0] if requesters else ""
        self._currently_playing = QueueItem.from_spotify_track(track, requester=requester)
        self._queue = [q for q in self._queue if q.track_uri != new_uri]
        self._bump_version()

    def _load_queue_from_spotify(self) -> None:
        items = self._spotify.fetch_tracks_for_playlist(self.playlist_id)
        self._queue = []
        for item in items:
            track = item.get("track")
            if track is None:
                continue
            requesters = self._requester_map.get(track["uri"])
            requester = requesters[0] if requesters else ""
            self._queue.append(QueueItem.from_spotify_track(track, requester=requester))

    def _bump_version(self) -> None:
        self._version += 1
        for callback in self._subscribers:
            callback()
