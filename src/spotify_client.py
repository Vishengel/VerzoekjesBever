from typing import ClassVar

from spotipy import CacheFileHandler, Spotify, SpotifyOAuth

from config import CONFIG
from models import PlaybackInfo, QueueItem


class SpotifyClient:
    SCOPE: ClassVar[list[str]] = [
        "user-read-currently-playing",
        "user-read-playback-state",
        "user-modify-playback-state",
    ]

    def __init__(self):
        CONFIG.cache_dir.mkdir(parents=True, exist_ok=True)
        self._sp = Spotify(
            auth_manager=SpotifyOAuth(
                client_id=CONFIG.spotipy_client_id,
                client_secret=CONFIG.spotipy_client_secret.get_secret_value(),
                redirect_uri=CONFIG.spotipy_redirect_uri,
                scope=self.SCOPE,
                cache_handler=CacheFileHandler(
                    cache_path=CONFIG.cache_dir / "credentials"
                ),
            )
        )

    def ensure_authenticated(self) -> None:
        self._sp.current_user()

    def search_tracks(self, query: str, limit: int = 10) -> list[QueueItem]:
        results = self._sp.search(q=query, type="track", limit=limit)
        return [
            QueueItem.from_spotify_track(t, requester="")
            for t in results["tracks"]["items"]
        ]

    def play_track(self, track_uri: str, device_id: str | None = None) -> None:
        self._sp.start_playback(device_id=device_id, uris=[track_uri])

    def pause(self, device_id: str | None = None) -> None:
        self._sp.pause_playback(device_id=device_id)

    def resume(self, device_id: str | None = None) -> None:
        self._sp.start_playback(device_id=device_id)

    def get_devices(self) -> list[dict]:
        result = self._sp.devices()
        return result.get("devices", [])

    def get_playback_state(self) -> PlaybackInfo | None:
        state = self._sp.current_playback()
        if state is None:
            return None
        item = state.get("item")
        return PlaybackInfo(
            is_playing=state.get("is_playing", False),
            progress_ms=state.get("progress_ms", 0),
            duration_ms=item.get("duration_ms", 0) if item else 0,
        )
