from pathlib import Path
from unittest.mock import MagicMock

import pytest

from models import PlaybackState, QueueItem
from party_service import PartyService
from persistence import QueueStore


def _track_dict(name: str = "Song", artist: str = "Artist", uri: str = "spotify:track:s1") -> dict:
    return {
        "name": name,
        "artists": [{"name": artist}],
        "album": {"images": [{"url": "https://img.com/art.jpg"}]},
        "uri": uri,
    }


@pytest.fixture
def mock_spotify():
    client = MagicMock()
    client.current_user_id = "testuser"
    return client


@pytest.fixture
def store(tmp_path: Path):
    return QueueStore(tmp_path / "session.json")


@pytest.fixture
def service(mock_spotify, store):
    return PartyService(spotify=mock_spotify, store=store)


def test_start_session(service, store):
    service.start_session("Party", "dev1")
    assert store.has_session
    assert store.session_name == "Party"
    assert store.device_id == "dev1"


def test_has_session(service):
    assert not service.has_session
    service.start_session("Party", "dev1")
    assert service.has_session


def test_search_songs(service, mock_spotify):
    mock_spotify.search_tracks.return_value = [_track_dict("Dancing Queen", "ABBA", "spotify:track:dq")]
    results = service.search_songs("Dancing Queen")
    assert len(results) == 1
    assert results[0].track_name == "Dancing Queen"
    assert results[0].requester == ""


def test_add_song_to_queue(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_song(track=_track_dict(), requester="Lisa")
    assert len(service.get_queue()) == 1
    assert service.get_queue()[0].requester == "Lisa"


def test_add_song_to_top(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_song(track=_track_dict("Song1", uri="spotify:track:s1"), requester="Lisa")
    service.add_song(track=_track_dict("Song2", uri="spotify:track:s2"), requester="Mark", top=True)
    assert service.get_queue()[0].track_name == "Song2"


def test_remove_from_queue(service):
    service.start_session("Party", "dev1")
    service.add_song(track=_track_dict(), requester="Lisa")
    service.remove_from_queue("spotify:track:s1")
    assert service.get_queue() == []


def test_move_to_top(service):
    service.start_session("Party", "dev1")
    service.add_song(track=_track_dict("S1", uri="spotify:track:s1"), requester="A")
    service.add_song(track=_track_dict("S2", uri="spotify:track:s2"), requester="B")
    service.add_song(track=_track_dict("S3", uri="spotify:track:s3"), requester="C")
    service.move_to_top("spotify:track:s3")
    assert service.get_queue()[0].track_name == "S3"


def test_play_next(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_song(track=_track_dict("Song1", uri="spotify:track:s1"), requester="Lisa")
    service.play_next()
    mock_spotify.play_track.assert_called_once_with("spotify:track:s1", device_id="dev1")
    assert service.get_currently_playing().track_name == "Song1"
    assert service.playback_state == PlaybackState.PLAYING
    assert service.get_queue() == []


def test_play_next_empty_queue(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.play_next()
    mock_spotify.play_track.assert_not_called()


def test_pause(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_song(track=_track_dict(), requester="Lisa")
    service.play_next()
    service.pause()
    mock_spotify.pause.assert_called_once_with(device_id="dev1")
    assert service.playback_state == PlaybackState.PAUSED


def test_resume(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_song(track=_track_dict(), requester="Lisa")
    service.play_next()
    service.pause()
    service.resume()
    mock_spotify.resume.assert_called_once_with(device_id="dev1")
    assert service.playback_state == PlaybackState.PLAYING


def test_set_device(service, store):
    service.start_session("Party", "dev1")
    service.set_device("dev2")
    assert store.device_id == "dev2"


def test_version_increments(service):
    v0 = service.version
    service.start_session("Party", "dev1")
    assert service.version > v0
    v1 = service.version
    service.add_song(track=_track_dict(), requester="Lisa")
    assert service.version > v1


def test_poll_detects_track_ended(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_song(track=_track_dict("Song1", uri="spotify:track:s1"), requester="Lisa")
    service.add_song(track=_track_dict("Song2", uri="spotify:track:s2"), requester="Mark")
    service.play_next()

    mock_spotify.get_playback_state.return_value = {
        "is_playing": False,
        "item": {"uri": "spotify:track:s1", "duration_ms": 200000},
        "progress_ms": 199000,
    }
    service.poll_playback()

    mock_spotify.play_track.assert_called_with("spotify:track:s2", device_id="dev1")
    assert service.get_currently_playing().track_name == "Song2"


def test_poll_track_ended_empty_queue_goes_idle(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_song(track=_track_dict(), requester="Lisa")
    service.play_next()

    mock_spotify.get_playback_state.return_value = {
        "is_playing": False,
        "item": {"uri": "spotify:track:s1", "duration_ms": 200000},
        "progress_ms": 199000,
    }
    service.poll_playback()

    assert service.playback_state == PlaybackState.IDLE
    assert service.get_currently_playing() is None


def test_poll_still_playing_no_change(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_song(track=_track_dict(), requester="Lisa")
    service.play_next()
    v = service.version

    mock_spotify.get_playback_state.return_value = {
        "is_playing": True,
        "item": {"uri": "spotify:track:s1", "duration_ms": 200000},
        "progress_ms": 50000,
    }
    service.poll_playback()

    assert service.version == v


def test_poll_no_playback_state(service, mock_spotify):
    mock_spotify.get_playback_state.return_value = None
    service.poll_playback()
    assert service.playback_state == PlaybackState.IDLE


def test_play_next_bumps_skip_version(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_song(track=_track_dict(), requester="Lisa")
    assert service.last_skip_version == 0
    service.play_next()
    assert service.last_skip_version == 1


def test_poll_track_end_does_not_bump_skip_version(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_song(track=_track_dict("Song1", uri="spotify:track:s1"), requester="Lisa")
    service.add_song(track=_track_dict("Song2", uri="spotify:track:s2"), requester="Mark")
    service.play_next()
    skip_v = service.last_skip_version

    mock_spotify.get_playback_state.return_value = {
        "is_playing": False,
        "item": {"uri": "spotify:track:s1", "duration_ms": 200000},
        "progress_ms": 199000,
    }
    service.poll_playback()
    assert service.last_skip_version == skip_v


def test_beaver_enabled_default_true(service):
    assert service.beaver_enabled is True


def test_set_beaver_enabled(service):
    service.set_beaver_enabled(False)
    assert service.beaver_enabled is False
    service.set_beaver_enabled(True)
    assert service.beaver_enabled is True


def test_update_requester(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_song(track=_track_dict(uri="spotify:track:s1"), requester="Typo")
    v = service.version
    service.update_requester("spotify:track:s1", "Fixed")
    assert service.get_queue()[0].requester == "Fixed"
    assert service.version > v


def test_get_known_requesters(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_song(track=_track_dict("S1", uri="spotify:track:s1"), requester="Alice")
    service.add_song(track=_track_dict("S2", uri="spotify:track:s2"), requester="Bob")
    service.add_song(track=_track_dict("S3", uri="spotify:track:s3"), requester="Alice")
    assert service.get_known_requesters() == ["Alice", "Bob"]


def test_get_known_requesters_includes_currently_playing(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_song(track=_track_dict("S1", uri="spotify:track:s1"), requester="Charlie")
    service.add_song(track=_track_dict("S2", uri="spotify:track:s2"), requester="Dana")
    service.play_next()
    assert "Charlie" in service.get_known_requesters()
    assert "Dana" in service.get_known_requesters()


def test_session_persists_across_restart(service, mock_spotify, tmp_path):
    service.start_session("Party", "dev1")
    service.add_song(track=_track_dict("Song1", uri="spotify:track:s1"), requester="Lisa")

    store2 = QueueStore(tmp_path / "session.json")
    svc2 = PartyService(spotify=mock_spotify, store=store2)
    assert svc2.has_session
    assert len(svc2.get_queue()) == 1
    assert svc2.get_queue()[0].track_name == "Song1"
