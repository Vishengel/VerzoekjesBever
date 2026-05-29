from typing import ClassVar

from spotipy import CacheFileHandler, Spotify, SpotifyOAuth

from config import CONFIG


class SpotifyClient(Spotify):
    SCOPE: ClassVar[list[str]] = [
        "user-read-currently-playing",
        "user-read-playback-state",
        "user-modify-playback-state",
    ]

    def __init__(self):
        CONFIG.cache_dir.mkdir(parents=True, exist_ok=True)
        super().__init__(
            auth_manager=SpotifyOAuth(
                client_id=CONFIG.spotipy_client_id,
                client_secret=CONFIG.spotipy_client_secret.get_secret_value(),
                redirect_uri=CONFIG.spotipy_redirect_uri,
                scope=self.SCOPE,
                cache_handler=CacheFileHandler(cache_path=CONFIG.cache_dir / "credentials"),
            )
        )

    @property
    def current_user_id(self) -> str:
        return self.current_user()["id"]

    def search_tracks(self, query: str, limit: int = 10) -> list[dict]:
        results = self.search(q=query, type="track", limit=limit)
        return results["tracks"]["items"]

    def play_track(self, track_uri: str, device_id: str | None = None) -> None:
        self.start_playback(device_id=device_id, uris=[track_uri])

    def pause(self, device_id: str | None = None) -> None:
        self.pause_playback(device_id=device_id)

    def resume(self, device_id: str | None = None) -> None:
        self.start_playback(device_id=device_id)

    def get_devices(self) -> list[dict]:
        result = self.devices()
        return result.get("devices", [])

    def get_playback_state(self) -> dict | None:
        return self.current_playback()
