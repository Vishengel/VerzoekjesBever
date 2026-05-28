from collections.abc import Callable
from typing import ClassVar

from spotipy import CacheFileHandler, Spotify, SpotifyOAuth

from config import CONFIG
from util import chunk_generator


class SpotifyClient(Spotify):
    SCOPE: ClassVar[list[str]] = [
        "user-library-read",
        "user-library-modify",
        "playlist-modify-public",
        "playlist-modify-private",
    ]
    GET_ITEM_LIMIT: ClassVar[int] = 50  # Spotify API allows up to 50 items per get request
    PUT_ITEM_LIMIT: ClassVar[int] = 100  # Spotify API allows up to 100 items per put request

    def __init__(self):
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

    def fetch_all_playlists(self, user_id: str) -> list[dict]:
        return self._fetch_paginated_items(self.user_playlists, user_id, limit=self.GET_ITEM_LIMIT)

    def fetch_tracks_for_playlist(self, playlist_id: str) -> list[dict]:
        return self._fetch_paginated_items(self.playlist_items, playlist_id, limit=self.GET_ITEM_LIMIT)

    def replace_tracks_in_playlist(self, playlist_id: str, track_uris: list[str]):
        self.playlist_replace_items(playlist_id, [])
        for chunk in chunk_generator(iterable=track_uris, n=self.PUT_ITEM_LIMIT):
            self.playlist_add_items(playlist_id, chunk)

    def _fetch_paginated_items(self, fetch_function: Callable, *args, **kwargs) -> list[dict]:
        items = []
        result = fetch_function(*args, **kwargs)
        items.extend(result["items"])
        while result := self.next(result):
            items.extend(result["items"])
        return items
