# VerzoekjesBever Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a party song request app where a DJ manages a Spotify playlist via NiceGUI, with a live audience beamer display.

**Architecture:** Layered — NiceGUI pages → PartyService (singleton) → SpotifyClient + JSON persistence. PartyService owns all state and business logic. NiceGUI pages only read/write through PartyService. A background timer polls Spotify for currently playing track.

**Tech Stack:** Python 3.12+, NiceGUI (Quasar/Tailwind), spotipy, pydantic-settings

---

## File Map

| File | Responsibility |
|---|---|
| `src/models.py` | `QueueItem` dataclass |
| `src/persistence.py` | JSON read/write for requester map |
| `src/spotify_client.py` | Existing client, extended with `search_tracks()` and `get_currently_playing()` |
| `src/party_service.py` | PartyService singleton — all business logic, state, notifications |
| `src/config.py` | Existing config, extended with persistence path |
| `src/main.py` | NiceGUI app entry point, page routing, background poller |
| `src/pages/startup.py` | Playlist selection/creation page (`/setup`) |
| `src/pages/dj.py` | DJ interface page (`/dj`) |
| `src/pages/audience.py` | Audience beamer display page (`/`) |
| `tests/test_models.py` | Model tests |
| `tests/test_persistence.py` | Persistence tests |
| `tests/test_party_service.py` | PartyService tests (mocked SpotifyClient) |

---

### Task 1: Project Setup — Dependencies and Config

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/config.py`

- [ ] **Step 1: Add nicegui dependency**

```toml
[project]
name = "verzoekjesbever"
version = "0.1.0"
description = "Party song request app — manage Spotify playlists with a DJ interface and audience beamer display"
requires-python = ">=3.12"
dependencies = [
    "spotipy>=2.26.0",
    "nicegui>=2.20.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
]
```

- [ ] **Step 2: Install dependencies**

Run: `cd /home/jellev/repos/personal/VerzoekjesBever && uv sync`
Expected: Dependencies install successfully.

- [ ] **Step 3: Extend config with persistence path**

In `src/config.py`, add the requester map file path:

```python
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict

from base_config import BaseConfig


class Config(BaseConfig):
    package_root: Path = Path(__file__).parent

    spotipy_client_id: str
    spotipy_client_secret: SecretStr
    spotipy_redirect_uri: str

    model_config = SettingsConfigDict(
        env_file=BaseConfig.project_root / ".env", env_file_encoding="utf-8", env_ignore_empty=True, extra="ignore"
    )

    @property
    def requester_map_path(self) -> Path:
        return self.cache_dir / "requester_map.json"


CONFIG = Config()
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock src/config.py
git commit -m "feat: add nicegui dependency and persistence config"
```

---

### Task 2: Data Model

**Files:**
- Create: `src/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_models.py
from models import QueueItem


def test_queue_item_creation():
    item = QueueItem(
        track_name="Dancing Queen",
        artist="ABBA",
        album_art_url="https://i.scdn.co/image/abc123",
        requester="Lisa",
        track_uri="spotify:track:0GjEhVFGZW8afUYGChu3Rr",
    )
    assert item.track_name == "Dancing Queen"
    assert item.artist == "ABBA"
    assert item.requester == "Lisa"


def test_queue_item_from_spotify_track():
    spotify_track = {
        "name": "Mr. Brightside",
        "artists": [{"name": "The Killers"}],
        "album": {"images": [{"url": "https://i.scdn.co/image/xyz"}]},
        "uri": "spotify:track:003vvx7Niy0yvhvHt4a68B",
    }
    item = QueueItem.from_spotify_track(spotify_track, requester="Mark")
    assert item.track_name == "Mr. Brightside"
    assert item.artist == "The Killers"
    assert item.album_art_url == "https://i.scdn.co/image/xyz"
    assert item.requester == "Mark"
    assert item.track_uri == "spotify:track:003vvx7Niy0yvhvHt4a68B"


def test_queue_item_from_spotify_track_no_album_art():
    spotify_track = {
        "name": "Some Song",
        "artists": [{"name": "Artist"}],
        "album": {"images": []},
        "uri": "spotify:track:abc",
    }
    item = QueueItem.from_spotify_track(spotify_track, requester="Guest")
    assert item.album_art_url == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/jellev/repos/personal/VerzoekjesBever && uv run pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'models'`

- [ ] **Step 3: Create conftest.py for import path**

```python
# tests/conftest.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

- [ ] **Step 4: Write implementation**

```python
# src/models.py
from dataclasses import dataclass


@dataclass
class QueueItem:
    track_name: str
    artist: str
    album_art_url: str
    requester: str
    track_uri: str

    @classmethod
    def from_spotify_track(cls, track: dict, requester: str) -> "QueueItem":
        images = track["album"]["images"]
        return cls(
            track_name=track["name"],
            artist=track["artists"][0]["name"],
            album_art_url=images[0]["url"] if images else "",
            requester=requester,
            track_uri=track["uri"],
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/jellev/repos/personal/VerzoekjesBever && uv run pytest tests/test_models.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add src/models.py tests/conftest.py tests/test_models.py
git commit -m "feat: add QueueItem data model with Spotify track factory"
```

---

### Task 3: Persistence Layer

**Files:**
- Create: `src/persistence.py`
- Create: `tests/test_persistence.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_persistence.py
from pathlib import Path

from persistence import RequesterMap


def test_add_and_get_requester(tmp_path: Path):
    path = tmp_path / "requester_map.json"
    rmap = RequesterMap(path)
    rmap.add("spotify:track:abc", "Lisa")
    assert rmap.get("spotify:track:abc") == ["Lisa"]


def test_duplicate_track_different_requesters(tmp_path: Path):
    path = tmp_path / "requester_map.json"
    rmap = RequesterMap(path)
    rmap.add("spotify:track:abc", "Lisa")
    rmap.add("spotify:track:abc", "Mark")
    assert rmap.get("spotify:track:abc") == ["Lisa", "Mark"]


def test_get_unknown_track_returns_empty_list(tmp_path: Path):
    path = tmp_path / "requester_map.json"
    rmap = RequesterMap(path)
    assert rmap.get("spotify:track:unknown") == []


def test_remove_track(tmp_path: Path):
    path = tmp_path / "requester_map.json"
    rmap = RequesterMap(path)
    rmap.add("spotify:track:abc", "Lisa")
    rmap.remove("spotify:track:abc")
    assert rmap.get("spotify:track:abc") == []


def test_persistence_survives_reload(tmp_path: Path):
    path = tmp_path / "requester_map.json"
    rmap1 = RequesterMap(path)
    rmap1.add("spotify:track:abc", "Lisa")

    rmap2 = RequesterMap(path)
    assert rmap2.get("spotify:track:abc") == ["Lisa"]


def test_persistence_file_created(tmp_path: Path):
    path = tmp_path / "requester_map.json"
    rmap = RequesterMap(path)
    rmap.add("spotify:track:abc", "Lisa")
    assert path.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/jellev/repos/personal/VerzoekjesBever && uv run pytest tests/test_persistence.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'persistence'`

- [ ] **Step 3: Write implementation**

```python
# src/persistence.py
import json
from pathlib import Path


class RequesterMap:
    def __init__(self, path: Path):
        self._path = path
        self._data: dict[str, list[str]] = {}
        self._load()

    def add(self, track_uri: str, requester: str) -> None:
        self._data.setdefault(track_uri, []).append(requester)
        self._save()

    def get(self, track_uri: str) -> list[str]:
        return list(self._data.get(track_uri, []))

    def remove(self, track_uri: str) -> None:
        self._data.pop(track_uri, None)
        self._save()

    def _load(self) -> None:
        if self._path.exists():
            self._data = json.loads(self._path.read_text())

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/jellev/repos/personal/VerzoekjesBever && uv run pytest tests/test_persistence.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/persistence.py tests/test_persistence.py
git commit -m "feat: add RequesterMap persistence layer"
```

---

### Task 4: Extend SpotifyClient

**Files:**
- Modify: `src/spotify_client.py`

- [ ] **Step 1: Add search_tracks and get_currently_playing methods**

```python
# src/spotify_client.py
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
        "user-read-currently-playing",
    ]
    GET_ITEM_LIMIT: ClassVar[int] = 50
    PUT_ITEM_LIMIT: ClassVar[int] = 100

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

    def search_tracks(self, query: str, limit: int = 10) -> list[dict]:
        results = self.search(q=query, type="track", limit=limit)
        return results["tracks"]["items"]

    def get_currently_playing_track(self) -> dict | None:
        result = self.currently_playing()
        if result and result.get("is_playing") and result.get("item"):
            return result["item"]
        return None

    def create_playlist(self, name: str) -> dict:
        return self.user_playlist_create(self.current_user_id, name, public=False)

    def add_track_to_playlist(self, playlist_id: str, track_uri: str, position: int | None = None) -> None:
        self.playlist_add_items(playlist_id, [track_uri], position=position)

    def remove_track_from_playlist(self, playlist_id: str, track_uri: str) -> None:
        self.playlist_remove_all_occurrences_of_items(playlist_id, [track_uri])

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
```

Note: `user-read-currently-playing` scope added. New methods: `search_tracks`, `get_currently_playing_track`, `create_playlist`, `add_track_to_playlist`, `remove_track_from_playlist`.

- [ ] **Step 2: Commit**

```bash
git add src/spotify_client.py
git commit -m "feat: extend SpotifyClient with search, currently playing, and playlist management"
```

---

### Task 5: PartyService

**Files:**
- Create: `src/party_service.py`
- Create: `tests/test_party_service.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_party_service.py
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from models import QueueItem
from party_service import PartyService
from persistence import RequesterMap


@pytest.fixture
def mock_spotify():
    client = MagicMock()
    client.current_user_id = "testuser"
    return client


@pytest.fixture
def requester_map(tmp_path: Path):
    return RequesterMap(tmp_path / "requester_map.json")


@pytest.fixture
def service(mock_spotify, requester_map):
    svc = PartyService(spotify=mock_spotify, requester_map=requester_map)
    svc.start_session(playlist_id="playlist123")
    return svc


def test_start_session_existing_playlist(mock_spotify, requester_map):
    mock_spotify.fetch_tracks_for_playlist.return_value = []
    svc = PartyService(spotify=mock_spotify, requester_map=requester_map)
    svc.start_session(playlist_id="playlist123")
    assert svc.playlist_id == "playlist123"


def test_start_session_create_new_playlist(mock_spotify, requester_map):
    mock_spotify.create_playlist.return_value = {"id": "new_playlist_id"}
    svc = PartyService(spotify=mock_spotify, requester_map=requester_map)
    svc.start_session(playlist_id=None, playlist_name="My Party")
    mock_spotify.create_playlist.assert_called_once_with("My Party")
    assert svc.playlist_id == "new_playlist_id"


def test_search_songs(service, mock_spotify):
    mock_spotify.search_tracks.return_value = [
        {
            "name": "Dancing Queen",
            "artists": [{"name": "ABBA"}],
            "album": {"images": [{"url": "https://img.com/dq.jpg"}]},
            "uri": "spotify:track:dq",
        }
    ]
    results = service.search_songs("Dancing Queen")
    assert len(results) == 1
    assert results[0].track_name == "Dancing Queen"
    assert results[0].requester == ""


def test_add_song_to_bottom(service, mock_spotify):
    service.add_song(
        track={"name": "Song", "artists": [{"name": "Artist"}], "album": {"images": []}, "uri": "spotify:track:s1"},
        requester="Lisa",
        top=False,
    )
    mock_spotify.add_track_to_playlist.assert_called_once_with("playlist123", "spotify:track:s1", position=None)
    assert service.get_queue()[0].requester == "Lisa"


def test_add_song_to_top(service, mock_spotify):
    service.add_song(
        track={"name": "Song1", "artists": [{"name": "A"}], "album": {"images": []}, "uri": "spotify:track:s1"},
        requester="Lisa",
        top=False,
    )
    service.add_song(
        track={"name": "Song2", "artists": [{"name": "B"}], "album": {"images": []}, "uri": "spotify:track:s2"},
        requester="Mark",
        top=True,
    )
    mock_spotify.add_track_to_playlist.assert_called_with("playlist123", "spotify:track:s2", position=0)
    queue = service.get_queue()
    assert queue[0].track_name == "Song2"
    assert queue[1].track_name == "Song1"


def test_remove_currently_playing(service, mock_spotify):
    service._currently_playing = QueueItem(
        track_name="Song",
        artist="Artist",
        album_art_url="",
        requester="Lisa",
        track_uri="spotify:track:s1",
    )
    service.remove_currently_playing()
    mock_spotify.remove_track_from_playlist.assert_called_once_with("playlist123", "spotify:track:s1")
    assert service.get_currently_playing() is None


def test_remove_currently_playing_when_nothing_playing(service):
    service.remove_currently_playing()
    # Should not raise


def test_get_queue_empty(service):
    assert service.get_queue() == []


def test_get_currently_playing_none(service):
    assert service.get_currently_playing() is None


def test_poll_updates_currently_playing(service, mock_spotify):
    mock_spotify.get_currently_playing_track.return_value = {
        "name": "Now Playing",
        "artists": [{"name": "Artist"}],
        "album": {"images": [{"url": "https://img.com/np.jpg"}]},
        "uri": "spotify:track:np",
    }
    service.poll_currently_playing()
    current = service.get_currently_playing()
    assert current is not None
    assert current.track_name == "Now Playing"


def test_poll_clears_currently_playing_when_nothing(service, mock_spotify):
    service._currently_playing = QueueItem(
        track_name="Old", artist="A", album_art_url="", requester="X", track_uri="spotify:track:old"
    )
    mock_spotify.get_currently_playing_track.return_value = None
    service.poll_currently_playing()
    assert service.get_currently_playing() is None


def test_subscriber_notified_on_add(service, mock_spotify):
    callback = MagicMock()
    service.subscribe(callback)
    service.add_song(
        track={"name": "Song", "artists": [{"name": "A"}], "album": {"images": []}, "uri": "spotify:track:s1"},
        requester="Lisa",
        top=False,
    )
    callback.assert_called_once()


def test_version_increments_on_change(service, mock_spotify):
    v1 = service.version
    service.add_song(
        track={"name": "Song", "artists": [{"name": "A"}], "album": {"images": []}, "uri": "spotify:track:s1"},
        requester="Lisa",
        top=False,
    )
    assert service.version > v1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/jellev/repos/personal/VerzoekjesBever && uv run pytest tests/test_party_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'party_service'`

- [ ] **Step 3: Write implementation**

```python
# src/party_service.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/jellev/repos/personal/VerzoekjesBever && uv run pytest tests/test_party_service.py -v`
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add src/party_service.py tests/test_party_service.py
git commit -m "feat: add PartyService with queue management and polling"
```

---

### Task 6: NiceGUI App Entry Point

**Files:**
- Create: `src/main.py`
- Create: `src/pages/__init__.py`

- [ ] **Step 1: Create the NiceGUI app with routing**

```python
# src/pages/__init__.py
```

```python
# src/main.py
from nicegui import app, ui

from config import CONFIG
from party_service import PartyService
from persistence import RequesterMap
from spotify_client import SpotifyClient

service: PartyService | None = None


def get_service() -> PartyService:
    global service
    if service is None:
        spotify = SpotifyClient()
        requester_map = RequesterMap(CONFIG.requester_map_path)
        service = PartyService(spotify=spotify, requester_map=requester_map)
    return service


def start_polling() -> None:
    svc = get_service()

    async def poll():
        svc.poll_currently_playing()

    ui.timer(3.0, poll)


# Import pages to register routes
from pages import audience, dj, startup  # noqa: E402, F401


def main():
    app.on_startup(start_polling)
    ui.run(title="VerzoekjesBever", favicon="🦫", dark=True, reload=False, show=False, port=8000)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add src/main.py src/pages/__init__.py
git commit -m "feat: add NiceGUI app entry point with routing and polling"
```

---

### Task 7: Startup Page

**Files:**
- Create: `src/pages/startup.py`

- [ ] **Step 1: Build the startup page**

```python
# src/pages/startup.py
from nicegui import ui

from main import get_service


@ui.page("/setup", title="VerzoekjesBever — Setup", dark=True)
def setup_page():
    svc = get_service()
    spotify = svc._spotify

    playlists = spotify.fetch_all_playlists(spotify.current_user_id)
    playlist_options = {p["id"]: p["name"] for p in playlists}

    with ui.column().classes("w-full max-w-lg mx-auto mt-16 gap-6"):
        ui.label("🦫").classes("text-6xl text-center w-full")
        ui.label("VerzoekjesBever").classes("text-3xl font-bold text-center w-full")
        ui.label("Setup your party playlist").classes("text-gray-400 text-center w-full")

        ui.separator()

        ui.label("Create a new playlist").classes("text-lg font-semibold")
        with ui.row().classes("w-full gap-2"):
            new_name = ui.input("Playlist name", value=f"VerzoekjesBever — Party").classes("flex-grow")
            ui.button(
                "Create",
                on_click=lambda: start_with_new(new_name.value),
            ).props("color=positive")

        ui.separator()

        ui.label("Or pick an existing playlist").classes("text-lg font-semibold")
        selected = ui.select(
            options=playlist_options,
            label="Select playlist",
        ).classes("w-full")
        ui.button(
            "Use this playlist",
            on_click=lambda: start_with_existing(selected.value),
        ).props("color=primary").classes("w-full")

    def start_with_new(name: str):
        svc.start_session(playlist_id=None, playlist_name=name)
        ui.navigate.to("/dj")

    def start_with_existing(playlist_id: str):
        if not playlist_id:
            ui.notify("Pick a playlist first", type="warning")
            return
        svc.start_session(playlist_id=playlist_id)
        ui.navigate.to("/dj")
```

- [ ] **Step 2: Commit**

```bash
git add src/pages/startup.py
git commit -m "feat: add startup page for playlist selection/creation"
```

---

### Task 8: DJ Interface Page

**Files:**
- Create: `src/pages/dj.py`

- [ ] **Step 1: Build the DJ page**

```python
# src/pages/dj.py
from nicegui import ui

from main import get_service
from models import QueueItem


@ui.page("/dj", title="VerzoekjesBever — DJ", dark=True)
def dj_page():
    svc = get_service()

    if svc.playlist_id is None:
        ui.navigate.to("/setup")
        return

    requester_input = None
    search_results_container = None

    with ui.row().classes("w-full h-screen gap-0"):
        # Left panel — Search
        with ui.column().classes("w-1/2 p-6 gap-4 border-r border-gray-700"):
            ui.label("🦫 VerzoekjesBever — DJ").classes("text-2xl font-bold")

            with ui.card().classes("w-full bg-gray-900"):
                ui.label("Requester name").classes("text-sm text-gray-400")
                requester_input = ui.input(placeholder="Guest name...").classes("w-full")

            with ui.row().classes("w-full gap-2"):
                search_input = ui.input(placeholder="Search song or artist...").classes("flex-grow")
                ui.button("Search", on_click=lambda: do_search(search_input.value)).props("color=primary")
                search_input.on("keydown.enter", lambda: do_search(search_input.value))

            search_results_container = ui.column().classes("w-full gap-2 overflow-auto")

        # Right panel — Queue
        with ui.column().classes("w-1/2 p-6 gap-4"):
            ui.label("Current Queue").classes("text-2xl font-bold")

            @ui.refreshable
            def queue_display():
                current = svc.get_currently_playing()
                if current:
                    with ui.card().classes("w-full bg-gray-900 border-2 border-green-500"):
                        ui.label("NOW PLAYING").classes("text-xs text-gray-400 tracking-widest")
                        with ui.row().classes("items-center gap-4"):
                            if current.album_art_url:
                                ui.image(current.album_art_url).classes("w-14 h-14 rounded")
                            with ui.column().classes("flex-grow gap-0"):
                                ui.label(current.track_name).classes("text-lg font-bold text-green-400")
                                ui.label(current.artist).classes("text-gray-400")
                                if current.requester:
                                    ui.label(f"Requested by {current.requester}").classes("text-sm text-orange-400")
                            ui.button(
                                "Remove",
                                on_click=lambda: remove_current(),
                            ).props("color=negative flat")

                ui.label("UP NEXT").classes("text-xs text-gray-400 tracking-widest mt-2")
                queue = svc.get_queue()
                if not queue:
                    ui.label("No songs in queue yet").classes("text-gray-500 italic")
                for i, item in enumerate(queue):
                    with ui.card().classes("w-full bg-gray-900"):
                        with ui.row().classes("items-center gap-3"):
                            ui.label(str(i + 1)).classes("text-gray-500 font-bold w-6 text-center")
                            if item.album_art_url:
                                ui.image(item.album_art_url).classes("w-10 h-10 rounded")
                            with ui.column().classes("flex-grow gap-0"):
                                ui.label(item.track_name).classes("font-semibold")
                                ui.label(item.artist).classes("text-sm text-gray-400")
                            if item.requester:
                                ui.label(item.requester).classes("text-sm text-orange-400")

            queue_display()

            local_version = {"v": svc.version}

            def check_updates():
                if svc.version != local_version["v"]:
                    local_version["v"] = svc.version
                    queue_display.refresh()

            ui.timer(1.0, check_updates)

    def do_search(query: str):
        if not query.strip():
            return
        results = svc.search_songs(query)
        search_results_container.clear()
        with search_results_container:
            if not results:
                ui.label("No results found").classes("text-gray-500 italic")
                return
            for track_result in results:
                render_search_result(track_result)

    def render_search_result(item: QueueItem):
        with ui.card().classes("w-full bg-gray-800"):
            with ui.row().classes("items-center gap-3"):
                if item.album_art_url:
                    ui.image(item.album_art_url).classes("w-12 h-12 rounded")
                with ui.column().classes("flex-grow gap-0"):
                    ui.label(item.track_name).classes("font-semibold")
                    ui.label(item.artist).classes("text-sm text-gray-400")
                ui.button(
                    "+ Add",
                    on_click=lambda i=item: add_song(i, top=False),
                ).props("color=primary dense")
                ui.button(
                    "⬆ Top",
                    on_click=lambda i=item: add_song(i, top=True),
                ).props("color=warning dense")

    def add_song(item: QueueItem, top: bool):
        requester = requester_input.value.strip() if requester_input.value else ""
        if not requester:
            ui.notify("Enter a requester name first", type="warning")
            return
        track_dict = {
            "name": item.track_name,
            "artists": [{"name": item.artist}],
            "album": {"images": [{"url": item.album_art_url}] if item.album_art_url else []},
            "uri": item.track_uri,
        }
        svc.add_song(track=track_dict, requester=requester, top=top)
        position = "top" if top else "queue"
        ui.notify(f"Added '{item.track_name}' to {position} for {requester}", type="positive")
        queue_display.refresh()

    def remove_current():
        svc.remove_currently_playing()
        ui.notify("Removed currently playing track", type="info")
        queue_display.refresh()
```

- [ ] **Step 2: Commit**

```bash
git add src/pages/dj.py
git commit -m "feat: add DJ interface page with search, add, and remove"
```

---

### Task 9: Audience Beamer Display Page

**Files:**
- Create: `src/pages/audience.py`

- [ ] **Step 1: Build the audience page**

```python
# src/pages/audience.py
from nicegui import ui

from main import get_service


@ui.page("/", title="VerzoekjesBever", dark=True)
def audience_page():
    svc = get_service()

    ui.add_head_html("""
    <style>
        body { background: linear-gradient(135deg, #0d0d1a 0%, #1a1a3e 100%) !important; }
    </style>
    """)

    with ui.column().classes("w-full max-w-3xl mx-auto p-8 gap-6"):
        # Header
        with ui.column().classes("items-center gap-1"):
            ui.label("🦫").classes("text-5xl")
            ui.label("VERZOEKJESBEVER").classes("text-2xl font-extrabold tracking-wide text-white")
            ui.label("REQUEST PARTY").classes("text-xs tracking-[0.3em] text-green-400")

        @ui.refreshable
        def playlist_display():
            current = svc.get_currently_playing()

            # Now playing card
            if current:
                with ui.card().classes("w-full bg-green-600 rounded-xl p-5"):
                    ui.label("NOW PLAYING").classes("text-xs tracking-[0.2em] text-white/70")
                    with ui.row().classes("items-center gap-5 mt-2"):
                        if current.album_art_url:
                            ui.image(current.album_art_url).classes("w-20 h-20 rounded-lg")
                        with ui.column().classes("gap-0"):
                            ui.label(current.track_name).classes("text-2xl font-extrabold text-white")
                            ui.label(current.artist).classes("text-lg text-white/85")
                            if current.requester:
                                ui.label(f"🎤 Requested by {current.requester}").classes(
                                    "text-sm text-white/60 mt-1"
                                )
            else:
                with ui.card().classes("w-full bg-gray-800 rounded-xl p-8 text-center"):
                    ui.label("🦫").classes("text-4xl")
                    ui.label("No song playing yet").classes("text-xl text-gray-400 mt-2")
                    ui.label("Make a request!").classes("text-gray-500")

            # Queue
            queue = svc.get_queue()
            if queue:
                ui.label("UP NEXT").classes("text-xs tracking-[0.2em] text-gray-500 mt-4")
                with ui.card().classes("w-full bg-white/5 rounded-xl p-1"):
                    for i, item in enumerate(queue):
                        border = "border-b border-white/5" if i < len(queue) - 1 else ""
                        with ui.row().classes(f"items-center gap-3 px-4 py-3 {border}"):
                            ui.label(str(i + 1)).classes("text-green-400 font-extrabold text-lg w-7 text-center")
                            if item.album_art_url:
                                ui.image(item.album_art_url).classes("w-11 h-11 rounded-md")
                            with ui.column().classes("flex-grow gap-0"):
                                ui.label(item.track_name).classes("text-white font-semibold text-base")
                                ui.label(item.artist).classes("text-gray-400 text-sm")
                            if item.requester:
                                ui.label(item.requester).classes("text-orange-400 text-sm")

        playlist_display()

        local_version = {"v": svc.version}

        def check_updates():
            if svc.version != local_version["v"]:
                local_version["v"] = svc.version
                playlist_display.refresh()

        ui.timer(1.0, check_updates)
```

- [ ] **Step 2: Commit**

```bash
git add src/pages/audience.py
git commit -m "feat: add audience beamer display with live updates"
```

---

### Task 10: Integration and Manual Testing

**Files:**
- All existing files

- [ ] **Step 1: Run all unit tests**

Run: `cd /home/jellev/repos/personal/VerzoekjesBever && uv run pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 2: Verify the app starts**

Run: `cd /home/jellev/repos/personal/VerzoekjesBever/src && uv run python main.py`

Check:
- App starts on `http://localhost:8000`
- Navigate to `http://localhost:8000/setup` — see playlist selection page
- Create or select a playlist → redirects to `/dj`
- Open `http://localhost:8000/` in another tab — see audience beamer display
- Search for a song in DJ view → results appear
- Enter requester name + click Add → song appears in DJ queue and beamer
- Add with Top → song appears at position 1
- Remove currently playing → track removed

- [ ] **Step 3: Fix any issues found during manual testing**

Iterate until all flows work correctly.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: VerzoekjesBever party request app — initial working version"
```
