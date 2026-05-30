from pathlib import Path
from unittest.mock import MagicMock

import pytest
from spotipy.exceptions import SpotifyException

from models import PartyEventType, PlaybackInfo, PlaybackState, QueueItem
from party_service import DEMO_QUEUE_SIZE, DEMO_SONG, PartyService
from persistence import QueueStore


def _make_item(
    name="Song", artist="Artist", uri="spotify:track:s1", requester=""
) -> QueueItem:
    return QueueItem(
        track_name=name,
        artist=artist,
        album_art_url="https://img.com/art.jpg",
        requester=requester,
        track_uri=uri,
    )


@pytest.fixture
def mock_spotify():
    return MagicMock()


@pytest.fixture
def store(tmp_path: Path):
    return QueueStore(tmp_path / "session.json")


@pytest.fixture
def service(mock_spotify, store):
    return PartyService(spotify=mock_spotify, store=store)


def test_start_session(service, store):
    service.start_session("Party", "dev1")
    pytest.assume(store.has_session)
    pytest.assume(store.session_name == "Party")
    pytest.assume(store.device_id == "dev1")


def test_has_session(service):
    pytest.assume(not service.has_session)
    service.start_session("Party", "dev1")
    pytest.assume(service.has_session)


def test_search_songs(service, mock_spotify):
    mock_spotify.search_tracks.return_value = [
        _make_item("Dancing Queen", artist="ABBA", uri="spotify:track:dq")
    ]
    results = service.search_songs("Dancing Queen")
    pytest.assume(len(results) == 1)
    pytest.assume(results[0].track_name == "Dancing Queen")


def test_add_to_queue(service):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item(requester="Lisa"))
    pytest.assume(len(service.get_queue()) == 1)
    pytest.assume(service.get_queue()[0].requester == "Lisa")


def test_add_to_queue_top(service):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1", requester="Lisa"))
    service.add_to_queue(
        _make_item("Song2", uri="spotify:track:s2", requester="Mark"), top=True
    )
    pytest.assume(service.get_queue()[0].track_name == "Song2")


def test_remove_from_queue(service):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item(requester="Lisa"))
    uid = service.get_queue()[0].uid
    service.remove_from_queue(uid)
    pytest.assume(service.get_queue() == [])


def test_move_to_top(service):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("S1", uri="spotify:track:s1", requester="A"))
    service.add_to_queue(_make_item("S2", uri="spotify:track:s2", requester="B"))
    service.add_to_queue(_make_item("S3", uri="spotify:track:s3", requester="C"))
    uid = service.get_queue()[2].uid
    service.move_to_top(uid)
    pytest.assume(service.get_queue()[0].track_name == "S3")


def test_move_up(service):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("S1", uri="spotify:track:s1", requester="A"))
    service.add_to_queue(_make_item("S2", uri="spotify:track:s2", requester="B"))
    service.add_to_queue(_make_item("S3", uri="spotify:track:s3", requester="C"))
    uid = service.get_queue()[2].uid
    service.move_up(uid)
    pytest.assume(service.get_queue()[1].track_name == "S3")
    pytest.assume(service.get_queue()[2].track_name == "S2")


def test_move_down(service):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("S1", uri="spotify:track:s1", requester="A"))
    service.add_to_queue(_make_item("S2", uri="spotify:track:s2", requester="B"))
    service.add_to_queue(_make_item("S3", uri="spotify:track:s3", requester="C"))
    uid = service.get_queue()[0].uid
    service.move_down(uid)
    pytest.assume(service.get_queue()[0].track_name == "S2")
    pytest.assume(service.get_queue()[1].track_name == "S1")


def test_move_up_bumps_version(service):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("S1", uri="spotify:track:s1"))
    service.add_to_queue(_make_item("S2", uri="spotify:track:s2"))
    v = service.version
    uid = service.get_queue()[1].uid
    service.move_up(uid)
    pytest.assume(service.version == v + 1)


def test_move_down_bumps_version(service):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("S1", uri="spotify:track:s1"))
    service.add_to_queue(_make_item("S2", uri="spotify:track:s2"))
    v = service.version
    uid = service.get_queue()[0].uid
    service.move_down(uid)
    pytest.assume(service.version == v + 1)


def test_play_next(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1", requester="Lisa"))
    service.play_next()
    mock_spotify.play_track.assert_called_once_with(
        "spotify:track:s1", device_id="dev1"
    )
    pytest.assume(service.get_currently_playing().track_name == "Song1")
    pytest.assume(service.playback_state == PlaybackState.PLAYING)
    pytest.assume(service.get_queue() == [])


def test_play_next_empty_queue(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.play_next()
    mock_spotify.play_track.assert_not_called()


def test_pause(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item(requester="Lisa"))
    service.play_next()
    service.pause()
    mock_spotify.pause.assert_called_once_with(device_id="dev1")
    pytest.assume(service.playback_state == PlaybackState.PAUSED)


def test_resume(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item(requester="Lisa"))
    service.play_next()
    service.pause()
    service.resume()
    mock_spotify.resume.assert_called_once_with(device_id="dev1")
    pytest.assume(service.playback_state == PlaybackState.PLAYING)


def test_set_device(service, store):
    service.start_session("Party", "dev1")
    service.set_device("dev2")
    pytest.assume(store.device_id == "dev2")


def test_version_increments(service):
    v0 = service.version
    service.start_session("Party", "dev1")
    pytest.assume(service.version > v0)
    v1 = service.version
    service.add_to_queue(_make_item(requester="Lisa"))
    pytest.assume(service.version > v1)


def test_poll_detects_track_ended(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1", requester="Lisa"))
    service.add_to_queue(_make_item("Song2", uri="spotify:track:s2", requester="Mark"))
    service.play_next()

    mock_spotify.get_playback_state.return_value = PlaybackInfo(
        is_playing=False,
        progress_ms=199000,
        duration_ms=200000,
        track_uri="spotify:track:s1",
    )
    service.poll_playback()

    mock_spotify.play_track.assert_called_with("spotify:track:s2", device_id="dev1")
    pytest.assume(service.get_currently_playing().track_name == "Song2")


def test_poll_track_ended_empty_queue_goes_idle(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item(requester="Lisa"))
    service.play_next()

    mock_spotify.get_playback_state.return_value = PlaybackInfo(
        is_playing=False,
        progress_ms=199000,
        duration_ms=200000,
        track_uri="spotify:track:s1",
    )
    service.poll_playback()

    pytest.assume(service.playback_state == PlaybackState.IDLE)
    pytest.assume(service.get_currently_playing() is None)


def test_poll_still_playing_no_change(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item(requester="Lisa"))
    service.play_next()
    v = service.version

    mock_spotify.get_playback_state.return_value = PlaybackInfo(
        is_playing=True,
        progress_ms=50000,
        duration_ms=200000,
        track_uri="spotify:track:s1",
    )
    service.poll_playback()

    pytest.assume(service.version == v)


def test_poll_no_playback_state(service, mock_spotify):
    mock_spotify.get_playback_state.return_value = None
    service.poll_playback()
    pytest.assume(service.playback_state == PlaybackState.IDLE)


def test_play_next_emits_skipped_event(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item(requester="Lisa"))
    v = service.version
    service.play_next()
    events = service.get_events_since(v)
    skipped = [e for e in events if e.kind == PartyEventType.SKIPPED]
    pytest.assume(len(skipped) == 1)
    pytest.assume(skipped[0].track_uri == "spotify:track:s1")


def test_poll_track_end_does_not_emit_skipped(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1", requester="Lisa"))
    service.add_to_queue(_make_item("Song2", uri="spotify:track:s2", requester="Mark"))
    service.play_next()
    v = service.version

    mock_spotify.get_playback_state.return_value = PlaybackInfo(
        is_playing=False,
        progress_ms=199000,
        duration_ms=200000,
        track_uri="spotify:track:s1",
    )
    service.poll_playback()
    skipped = [
        e for e in service.get_events_since(v) if e.kind == PartyEventType.SKIPPED
    ]
    pytest.assume(len(skipped) == 0)


def test_beaver_enabled_default_false(service):
    pytest.assume(service.beaver_enabled is False)


def test_set_beaver_enabled(service):
    service.set_beaver_enabled(False)
    pytest.assume(service.beaver_enabled is False)
    service.set_beaver_enabled(True)
    pytest.assume(service.beaver_enabled is True)


def test_update_requester(service):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item(uri="spotify:track:s1", requester="Typo"))
    uid = service.get_queue()[0].uid
    v = service.version
    service.update_requester(uid, "Fixed")
    pytest.assume(service.get_queue()[0].requester == "Fixed")
    pytest.assume(service.version > v)


def test_get_known_requesters(service):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("S1", uri="spotify:track:s1", requester="Alice"))
    service.add_to_queue(_make_item("S2", uri="spotify:track:s2", requester="Bob"))
    service.add_to_queue(_make_item("S3", uri="spotify:track:s3", requester="Alice"))
    pytest.assume(service.get_known_requesters() == ["Alice", "Bob"])


def test_get_known_requesters_includes_currently_playing(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("S1", uri="spotify:track:s1", requester="Charlie"))
    service.add_to_queue(_make_item("S2", uri="spotify:track:s2", requester="Dana"))
    service.play_next()
    pytest.assume("Charlie" in service.get_known_requesters())
    pytest.assume("Dana" in service.get_known_requesters())


def test_add_to_queue_emits_added_event(service):
    service.start_session("Party", "dev1")
    v = service.version
    service.add_to_queue(_make_item(requester="Lisa"))
    events = service.get_events_since(v)
    added = [e for e in events if e.kind == PartyEventType.ADDED]
    pytest.assume(len(added) == 1)
    pytest.assume(added[0].track_uri == "spotify:track:s1")
    pytest.assume(added[0].is_priority is False)


def test_add_to_queue_event_tracks_uri(service):
    service.start_session("Party", "dev1")
    v = service.version
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1", requester="Lisa"))
    service.add_to_queue(_make_item("Song2", uri="spotify:track:s2", requester="Mark"))
    events = service.get_events_since(v)
    added = [e for e in events if e.kind == PartyEventType.ADDED]
    pytest.assume(len(added) == 2)
    pytest.assume(added[0].track_uri == "spotify:track:s1")
    pytest.assume(added[1].track_uri == "spotify:track:s2")


def test_add_to_queue_event_tracks_priority(service):
    service.start_session("Party", "dev1")
    v = service.version
    service.add_to_queue(_make_item(requester="Lisa"), top=True)
    service.add_to_queue(
        _make_item("S2", uri="spotify:track:s2", requester="Mark"), top=False
    )
    events = service.get_events_since(v)
    added = [e for e in events if e.kind == PartyEventType.ADDED]
    pytest.assume(added[0].is_priority is True)
    pytest.assume(added[1].is_priority is False)


def test_play_next_does_not_emit_added(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item(requester="Lisa"))
    v = service.version
    service.play_next()
    added = [e for e in service.get_events_since(v) if e.kind == PartyEventType.ADDED]
    pytest.assume(len(added) == 0)


def test_move_to_top_emits_event(service):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("S1", uri="spotify:track:s1", requester="A"))
    service.add_to_queue(_make_item("S2", uri="spotify:track:s2", requester="B"))
    v = service.version
    uid = service.get_queue()[1].uid
    service.move_to_top(uid)
    events = service.get_events_since(v)
    moved = [e for e in events if e.kind == PartyEventType.MOVED_TO_TOP]
    pytest.assume(len(moved) == 1)
    pytest.assume(moved[0].track_uri == "spotify:track:s2")


def test_events_pruned_beyond_max(service):
    service.start_session("Party", "dev1")
    for i in range(60):
        service.add_to_queue(
            _make_item(f"S{i}", uri=f"spotify:track:s{i}", requester="X")
        )
    events = service.get_events_since(0)
    pytest.assume(len(events) <= PartyService.MAX_EVENTS)


def test_get_events_since_filters_by_version(service):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("S1", uri="spotify:track:s1", requester="A"))
    v = service.version
    service.add_to_queue(_make_item("S2", uri="spotify:track:s2", requester="B"))
    events = service.get_events_since(v)
    pytest.assume(len(events) == 1)
    pytest.assume(events[0].track_uri == "spotify:track:s2")


def test_session_persists_across_restart(service, mock_spotify, tmp_path):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1", requester="Lisa"))

    store2 = QueueStore(tmp_path / "session.json")
    svc2 = PartyService(spotify=mock_spotify, store=store2)
    pytest.assume(svc2.has_session)
    pytest.assume(len(svc2.get_queue()) == 1)
    pytest.assume(svc2.get_queue()[0].track_name == "Song1")


# --- Playback desync bug fixes ---


def test_poll_state_none_advances_queue(service, mock_spotify):
    """DJ skips in Spotify, playback stops → app plays next from queue."""
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1", requester="Lisa"))
    service.add_to_queue(_make_item("Song2", uri="spotify:track:s2", requester="Mark"))
    service.play_next()

    mock_spotify.get_playback_state.return_value = None
    service.poll_playback()

    mock_spotify.play_track.assert_called_with("spotify:track:s2", device_id="dev1")
    pytest.assume(service.get_currently_playing().track_name == "Song2")
    pytest.assume(service.playback_state == PlaybackState.PLAYING)


def test_poll_state_none_empty_queue_goes_idle(service, mock_spotify):
    """Playback stops with empty queue → IDLE."""
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item(requester="Lisa"))
    service.play_next()

    mock_spotify.get_playback_state.return_value = None
    service.poll_playback()

    pytest.assume(service.get_currently_playing() is None)
    pytest.assume(service.playback_state == PlaybackState.IDLE)


def test_poll_state_none_play_fails_requeues(service, mock_spotify):
    """Device unavailable → re-queue item instead of losing it."""
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1", requester="Lisa"))
    service.add_to_queue(_make_item("Song2", uri="spotify:track:s2", requester="Mark"))
    service.play_next()

    mock_spotify.get_playback_state.return_value = None
    mock_spotify.play_track.side_effect = SpotifyException(
        404, "https://api.spotify.com", msg="Device not found"
    )
    service.poll_playback()

    pytest.assume(service.playback_state == PlaybackState.IDLE)
    pytest.assume(len(service.get_queue()) == 1)
    pytest.assume(service.get_queue()[0].track_name == "Song2")


def test_poll_syncs_external_pause(service, mock_spotify):
    """DJ pauses in Spotify app → app syncs to PAUSED."""
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item(requester="Lisa"))
    service.play_next()

    mock_spotify.get_playback_state.return_value = PlaybackInfo(
        is_playing=False,
        progress_ms=100000,
        duration_ms=200000,
        track_uri="spotify:track:s1",
    )
    service.poll_playback()

    pytest.assume(service.playback_state == PlaybackState.PAUSED)


def test_poll_syncs_external_resume(service, mock_spotify):
    """DJ resumes in Spotify app → app syncs to PLAYING."""
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item(requester="Lisa"))
    service.play_next()
    service.pause()

    mock_spotify.get_playback_state.return_value = PlaybackInfo(
        is_playing=True,
        progress_ms=100000,
        duration_ms=200000,
        track_uri="spotify:track:s1",
    )
    service.poll_playback()

    pytest.assume(service.playback_state == PlaybackState.PLAYING)


def test_poll_track_ended_play_fails_requeues(service, mock_spotify):
    """Track ends naturally but next play fails → re-queue, don't lose song."""
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1", requester="Lisa"))
    service.add_to_queue(_make_item("Song2", uri="spotify:track:s2", requester="Mark"))
    service.play_next()

    mock_spotify.get_playback_state.return_value = PlaybackInfo(
        is_playing=False,
        progress_ms=199000,
        duration_ms=200000,
        track_uri="spotify:track:s1",
    )
    mock_spotify.play_track.side_effect = SpotifyException(
        404, "https://api.spotify.com", msg="Device not found"
    )
    service.poll_playback()

    pytest.assume(service.playback_state == PlaybackState.IDLE)
    pytest.assume(len(service.get_queue()) == 1)
    pytest.assume(service.get_queue()[0].track_name == "Song2")


# --- Track URI detection ---


def test_poll_track_uri_gone_advances_queue(service, mock_spotify):
    """Spotify clears item after track ends → advance queue."""
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1", requester="Lisa"))
    service.add_to_queue(_make_item("Song2", uri="spotify:track:s2", requester="Mark"))
    service.play_next()

    mock_spotify.get_playback_state.return_value = PlaybackInfo(
        is_playing=False, progress_ms=0, duration_ms=0, track_uri=None
    )
    service.poll_playback()

    mock_spotify.play_track.assert_called_with("spotify:track:s2", device_id="dev1")
    pytest.assume(service.get_currently_playing().track_name == "Song2")


def test_poll_different_track_uri_advances_queue(service, mock_spotify):
    """Spotify autoplay started different track → advance our queue."""
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1", requester="Lisa"))
    service.add_to_queue(_make_item("Song2", uri="spotify:track:s2", requester="Mark"))
    service.play_next()

    mock_spotify.get_playback_state.return_value = PlaybackInfo(
        is_playing=True,
        progress_ms=5000,
        duration_ms=180000,
        track_uri="spotify:track:autoplay",
    )
    service.poll_playback()

    mock_spotify.play_track.assert_called_with("spotify:track:s2", device_id="dev1")
    pytest.assume(service.get_currently_playing().track_name == "Song2")


# --- Demo queue ---


def test_start_session_with_demo(service):
    service.start_session("Party", "dev1", demo=True)
    pytest.assume(len(service.get_queue()) == DEMO_QUEUE_SIZE)
    pytest.assume(service.demo_queue_active is True)
    pytest.assume(service.get_queue()[0].track_name == DEMO_SONG.track_name)
    pytest.assume(service.get_queue()[0].requester == "🦫")


def test_demo_queue_all_unique_uids(service):
    service.start_session("Party", "dev1", demo=True)
    uids = [item.uid for item in service.get_queue()]
    pytest.assume(len(set(uids)) == DEMO_QUEUE_SIZE)


def test_demo_queue_cleared_on_first_add(service):
    service.start_session("Party", "dev1", demo=True)
    pytest.assume(len(service.get_queue()) == DEMO_QUEUE_SIZE)

    real_song = _make_item("Real Song", uri="spotify:track:real", requester="Alice")
    service.add_to_queue(real_song)

    pytest.assume(len(service.get_queue()) == 1)
    pytest.assume(service.get_queue()[0].track_name == "Real Song")
    pytest.assume(service.demo_queue_active is False)


def test_demo_queue_second_add_normal(service):
    service.start_session("Party", "dev1", demo=True)
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1", requester="A"))
    service.add_to_queue(_make_item("Song2", uri="spotify:track:s2", requester="B"))
    pytest.assume(len(service.get_queue()) == 2)


def test_demo_queue_persists_across_restart(mock_spotify, tmp_path):
    store1 = QueueStore(tmp_path / "session.json")
    svc1 = PartyService(spotify=mock_spotify, store=store1)
    svc1.start_session("Party", "dev1", demo=True)

    store2 = QueueStore(tmp_path / "session.json")
    svc2 = PartyService(spotify=mock_spotify, store=store2)
    pytest.assume(svc2.demo_queue_active is True)
    pytest.assume(len(svc2.get_queue()) == DEMO_QUEUE_SIZE)


def test_start_session_without_demo(service):
    service.start_session("Party", "dev1", demo=False)
    pytest.assume(len(service.get_queue()) == 0)
    pytest.assume(service.demo_queue_active is False)


def test_is_authenticated(service, mock_spotify):
    mock_spotify.is_authenticated.return_value = True
    pytest.assume(service.is_authenticated() is True)
    mock_spotify.is_authenticated.return_value = False
    pytest.assume(service.is_authenticated() is False)


def test_get_auth_url(service, mock_spotify):
    mock_spotify.get_auth_url.return_value = (
        "https://accounts.spotify.com/authorize?..."
    )
    pytest.assume(
        service.get_auth_url() == "https://accounts.spotify.com/authorize?..."
    )


def test_handle_auth_callback(service, mock_spotify):
    service.handle_auth_callback("test-code")
    mock_spotify.handle_auth_callback.assert_called_once_with("test-code")
