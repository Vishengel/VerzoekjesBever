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
