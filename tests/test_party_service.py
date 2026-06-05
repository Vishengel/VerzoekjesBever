from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from spotipy.exceptions import SpotifyException

from models import (
    PartyEventType,
    PlaybackInfo,
    PlaybackSignal,
    PlaybackState,
    QueueItem,
)
from adem_mode import ADEM_MODE_QUEUE_SIZE, ADEMNOOD_ITEM
from party_service import PartyService, detect_playback_signal
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


def test_restart_mid_playback_does_not_spuriously_advance(mock_spotify, store):
    # A session was playing; then the server process restarts (settle period,
    # held only in memory, is lost). Simulate by building a fresh service on a
    # store that already has a playing track.
    store.start_session("Party", "dev1")
    store.set_currently_playing(
        _make_item("Song1", uri="spotify:track:s1"), PlaybackState.PLAYING
    )
    store.add_to_queue(_make_item("Song2", uri="spotify:track:s2"))

    restarted = PartyService(spotify=mock_spotify, store=store)

    # First poll after restart: Spotify hasn't reported the track yet.
    mock_spotify.get_playback_state.return_value = None
    restarted.poll_playback()

    # The seeded settle window must suppress the TRACK_LOST verdict.
    pytest.assume(restarted.get_currently_playing().track_name == "Song1")
    mock_spotify.play_track.assert_not_called()


def test_detect_stopped_after_near_end_is_track_ended():
    # Device stops and resets progress to 0 at end; high-water near duration.
    info = PlaybackInfo(
        is_playing=False, progress_ms=0, duration_ms=200000, track_uri="u"
    )
    signal = detect_playback_signal(
        info, "u", PlaybackState.PLAYING, False, last_progress_ms=199000
    )
    pytest.assume(signal == PlaybackSignal.TRACK_ENDED)


def test_detect_stopped_mid_track_is_external_pause():
    # Same instantaneous state, but high-water is mid-track -> a real pause.
    info = PlaybackInfo(
        is_playing=False, progress_ms=0, duration_ms=200000, track_uri="u"
    )
    signal = detect_playback_signal(
        info, "u", PlaybackState.PLAYING, False, last_progress_ms=50000
    )
    pytest.assume(signal == PlaybackSignal.EXTERNAL_PAUSE)


def test_poll_track_end_with_progress_reset_advances(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1"))
    service.add_to_queue(_make_item("Song2", uri="spotify:track:s2"))
    service.play_next()  # current = Song1, high-water reset to 0

    # Plays to near the end (records the high-water mark).
    mock_spotify.get_playback_state.return_value = PlaybackInfo(
        is_playing=True,
        progress_ms=133144,
        duration_ms=133600,
        track_uri="spotify:track:s1",
    )
    service.poll_playback()

    # Device stops and resets progress to 0 -> looks like a pause, but isn't.
    mock_spotify.get_playback_state.return_value = PlaybackInfo(
        is_playing=False,
        progress_ms=0,
        duration_ms=133600,
        track_uri="spotify:track:s1",
    )
    service.poll_playback()

    pytest.assume(service.get_currently_playing().track_name == "Song2")
    pytest.assume(service.playback_state == PlaybackState.PLAYING)


def test_poll_mid_track_pause_not_treated_as_end(service, mock_spotify):
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1"))
    service.add_to_queue(_make_item("Song2", uri="spotify:track:s2"))
    service.play_next()

    mock_spotify.get_playback_state.return_value = PlaybackInfo(
        is_playing=True,
        progress_ms=40000,
        duration_ms=133600,
        track_uri="spotify:track:s1",
    )
    service.poll_playback()  # high-water = 40000 (mid-track)

    mock_spotify.get_playback_state.return_value = PlaybackInfo(
        is_playing=False,
        progress_ms=0,
        duration_ms=133600,
        track_uri="spotify:track:s1",
    )
    service.poll_playback()

    pytest.assume(service.playback_state == PlaybackState.PAUSED)
    pytest.assume(service.get_currently_playing().track_name == "Song1")


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


def test_play_next_play_fails_requeues(service, mock_spotify):
    """Manual skip but play fails → re-queue, don't lose song, stay idle."""
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1", requester="Lisa"))
    mock_spotify.play_track.side_effect = SpotifyException(
        404, "https://api.spotify.com", msg="Device not found"
    )
    v = service.version
    service.play_next()

    pytest.assume(len(service.get_queue()) == 1)
    pytest.assume(service.get_queue()[0].track_name == "Song1")
    pytest.assume(service.get_currently_playing() is None)
    skipped = [
        e for e in service.get_events_since(v) if e.kind == PartyEventType.SKIPPED
    ]
    pytest.assume(len(skipped) == 0)


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


def test_beaver_enabled_default_true(service):
    pytest.assume(service.beaver_enabled is True)


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


def test_get_requester_by_uid(service, store):
    item = _make_item(uri="spotify:track:gr", requester="Bob")
    store.add_to_queue(item)
    uid = store.queue[0].uid
    pytest.assume(service.get_requester(uid) == "Bob")
    pytest.assume(service.get_requester("nope") == "")


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


# --- Settle period (Spotify API latency guard) ---


def test_poll_ignores_none_during_settle_period(service, mock_spotify):
    """Spotify API hasn't registered new track yet → don't advance."""
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1", requester="Lisa"))
    service.play_next()

    mock_spotify.get_playback_state.return_value = None
    service.poll_playback()

    pytest.assume(service.get_currently_playing().track_name == "Song1")
    pytest.assume(service.playback_state == PlaybackState.PLAYING)


def test_poll_ignores_wrong_track_during_settle_period(service, mock_spotify):
    """Spotify still reports old track during settle → don't advance."""
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1", requester="Lisa"))
    service.add_to_queue(_make_item("Song2", uri="spotify:track:s2", requester="Mark"))
    service.play_next()

    mock_spotify.get_playback_state.return_value = PlaybackInfo(
        is_playing=True,
        progress_ms=5000,
        duration_ms=180000,
        track_uri="spotify:track:old",
    )
    service.poll_playback()

    pytest.assume(service.get_currently_playing().track_name == "Song1")
    pytest.assume(len(service.get_queue()) == 1)


# --- Playback desync bug fixes ---


def test_poll_state_none_advances_queue(service, mock_spotify):
    """DJ skips in Spotify, playback stops → app plays next from queue."""
    service.start_session("Party", "dev1")
    service.add_to_queue(_make_item("Song1", uri="spotify:track:s1", requester="Lisa"))
    service.add_to_queue(_make_item("Song2", uri="spotify:track:s2", requester="Mark"))
    service.play_next()

    service._playback_commanded_at = 0
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

    service._playback_commanded_at = 0
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

    service._playback_commanded_at = 0
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

    service._playback_commanded_at = 0
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

    service._playback_commanded_at = 0
    mock_spotify.get_playback_state.return_value = PlaybackInfo(
        is_playing=True,
        progress_ms=5000,
        duration_ms=180000,
        track_uri="spotify:track:autoplay",
    )
    service.poll_playback()

    mock_spotify.play_track.assert_called_with("spotify:track:s2", device_id="dev1")
    pytest.assume(service.get_currently_playing().track_name == "Song2")


# --- Adem-mode ---


def test_start_session_with_adem_mode(service):
    service.start_session("Party", "dev1", adem_mode=True)
    pytest.assume(len(service.get_queue()) == ADEM_MODE_QUEUE_SIZE)
    pytest.assume(service.adem_mode_active is True)
    pytest.assume(service.get_queue()[0].track_name == ADEMNOOD_ITEM.track_name)
    pytest.assume(service.get_queue()[0].requester == "🦫")


def test_adem_queue_all_unique_uids(service):
    service.start_session("Party", "dev1", adem_mode=True)
    uids = [item.uid for item in service.get_queue()]
    pytest.assume(len(set(uids)) == ADEM_MODE_QUEUE_SIZE)


def test_add_clears_adem_songs_but_keeps_mode(service):
    service.start_session("Party", "dev1", adem_mode=True)
    pytest.assume(len(service.get_queue()) == ADEM_MODE_QUEUE_SIZE)

    service.add_to_queue(
        _make_item("Real Song", uri="spotify:track:real", requester="Alice")
    )

    pytest.assume(len(service.get_queue()) == 1)
    pytest.assume(service.get_queue()[0].track_name == "Real Song")
    pytest.assume(service.adem_mode_active is True)


def test_second_add_keeps_first_song(service):
    service.start_session("Party", "dev1", adem_mode=True)
    service.add_to_queue(_make_item("Song A", uri="spotify:track:a", requester="Alice"))
    service.add_to_queue(_make_item("Song B", uri="spotify:track:b", requester="Bob"))

    pytest.assume(len(service.get_queue()) == 2)
    pytest.assume(service.get_queue()[0].track_name == "Song A")
    pytest.assume(service.get_queue()[1].track_name == "Song B")
    pytest.assume(service.adem_mode_active is True)


def test_adem_refills_after_real_songs_drain(service, mock_spotify):
    service.start_session("Party", "dev1", adem_mode=True)
    service.add_to_queue(
        _make_item("Real Song", uri="spotify:track:real", requester="Alice")
    )
    service.play_next()

    mock_spotify.get_playback_state.return_value = None
    service._playback_commanded_at = 0
    service.poll_playback()

    pytest.assume(service.adem_mode_active is True)
    pytest.assume(len(service.get_queue()) == ADEM_MODE_QUEUE_SIZE - 1)
    pytest.assume(
        service.get_currently_playing().track_name == ADEMNOOD_ITEM.track_name
    )


def test_adem_queue_persists_across_restart(mock_spotify, tmp_path):
    store1 = QueueStore(tmp_path / "session.json")
    svc1 = PartyService(spotify=mock_spotify, store=store1)
    svc1.start_session("Party", "dev1", adem_mode=True)

    store2 = QueueStore(tmp_path / "session.json")
    svc2 = PartyService(spotify=mock_spotify, store=store2)
    pytest.assume(svc2.adem_mode_active is True)
    pytest.assume(len(svc2.get_queue()) == ADEM_MODE_QUEUE_SIZE)


def test_start_session_without_adem_mode(service):
    service.start_session("Party", "dev1", adem_mode=False)
    pytest.assume(len(service.get_queue()) == 0)
    pytest.assume(service.adem_mode_active is False)


def test_adem_mode_refills_queue_while_playing(service, mock_spotify):
    service.start_session("Party", "dev1", adem_mode=True)
    service.play_next()
    pytest.assume(service.get_currently_playing() is not None)

    for _ in range(ADEM_MODE_QUEUE_SIZE - 1):
        service.play_next()

    mock_spotify.get_playback_state.return_value = PlaybackInfo(
        is_playing=True,
        progress_ms=10000,
        duration_ms=200000,
        track_uri=service.get_currently_playing().track_uri,
    )
    service.poll_playback()

    pytest.assume(len(service.get_queue()) == ADEM_MODE_QUEUE_SIZE)
    pytest.assume(service.adem_mode_active is True)


def test_adem_mode_refills_on_advance_when_empty(service, mock_spotify):
    service.start_session("Party", "dev1", adem_mode=True)
    service.play_next()

    for _ in range(ADEM_MODE_QUEUE_SIZE - 1):
        service.play_next()

    service._playback_commanded_at = 0
    mock_spotify.get_playback_state.return_value = None
    service.poll_playback()

    pytest.assume(len(service.get_queue()) == ADEM_MODE_QUEUE_SIZE - 1)
    pytest.assume(
        service.get_currently_playing().track_name == ADEMNOOD_ITEM.track_name
    )
    pytest.assume(service.adem_mode_active is True)


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


# --- detect_playback_signal ---

_SIG_URI = "spotify:track:abc"


def _playing_info(track_uri=_SIG_URI, progress_ms=10000, duration_ms=200000):
    return PlaybackInfo(
        is_playing=True,
        progress_ms=progress_ms,
        duration_ms=duration_ms,
        track_uri=track_uri,
    )


def _paused_info(track_uri=_SIG_URI, progress_ms=10000, duration_ms=200000):
    return PlaybackInfo(
        is_playing=False,
        progress_ms=progress_ms,
        duration_ms=duration_ms,
        track_uri=track_uri,
    )


def test_signal_no_info_no_current_track():
    result = detect_playback_signal(
        info=None,
        current_track_uri=None,
        our_state=PlaybackState.PLAYING,
        in_settle_period=False,
    )
    pytest.assume(result == PlaybackSignal.NOTHING)


def test_signal_no_info_has_current_in_settle():
    result = detect_playback_signal(
        info=None,
        current_track_uri=_SIG_URI,
        our_state=PlaybackState.PLAYING,
        in_settle_period=True,
    )
    pytest.assume(result == PlaybackSignal.NOTHING)


def test_signal_no_info_has_current_not_in_settle():
    result = detect_playback_signal(
        info=None,
        current_track_uri=_SIG_URI,
        our_state=PlaybackState.PLAYING,
        in_settle_period=False,
    )
    pytest.assume(result == PlaybackSignal.TRACK_LOST)


def test_signal_wrong_track_in_settle():
    result = detect_playback_signal(
        info=_playing_info(track_uri="spotify:track:other"),
        current_track_uri=_SIG_URI,
        our_state=PlaybackState.PLAYING,
        in_settle_period=True,
    )
    pytest.assume(result == PlaybackSignal.NOTHING)


def test_signal_wrong_track_not_in_settle():
    result = detect_playback_signal(
        info=_playing_info(track_uri="spotify:track:other"),
        current_track_uri=_SIG_URI,
        our_state=PlaybackState.PLAYING,
        in_settle_period=False,
    )
    pytest.assume(result == PlaybackSignal.TRACK_LOST)


def test_signal_track_ended():
    result = detect_playback_signal(
        info=_paused_info(progress_ms=198000, duration_ms=200000),
        current_track_uri=_SIG_URI,
        our_state=PlaybackState.PLAYING,
        in_settle_period=False,
    )
    pytest.assume(result == PlaybackSignal.TRACK_ENDED)


def test_signal_track_ended_progress_pegged_still_playing():
    """Natural track end in isolation: Spotify keeps reporting is_playing=True
    with progress_ms pegged exactly at duration_ms (observed 2026-06-03)."""
    result = detect_playback_signal(
        info=_playing_info(progress_ms=133600, duration_ms=133600),
        current_track_uri=_SIG_URI,
        our_state=PlaybackState.PLAYING,
        in_settle_period=False,
    )
    pytest.assume(result == PlaybackSignal.TRACK_ENDED)


def test_signal_external_resume():
    result = detect_playback_signal(
        info=_playing_info(),
        current_track_uri=_SIG_URI,
        our_state=PlaybackState.PAUSED,
        in_settle_period=False,
    )
    pytest.assume(result == PlaybackSignal.EXTERNAL_RESUME)


def test_signal_external_pause():
    result = detect_playback_signal(
        info=_paused_info(progress_ms=50000, duration_ms=200000),
        current_track_uri=_SIG_URI,
        our_state=PlaybackState.PLAYING,
        in_settle_period=False,
    )
    pytest.assume(result == PlaybackSignal.EXTERNAL_PAUSE)


def test_signal_playing_and_we_think_playing():
    result = detect_playback_signal(
        info=_playing_info(),
        current_track_uri=_SIG_URI,
        our_state=PlaybackState.PLAYING,
        in_settle_period=False,
    )
    pytest.assume(result == PlaybackSignal.NOTHING)


def test_signal_paused_and_we_think_paused():
    result = detect_playback_signal(
        info=_paused_info(progress_ms=50000, duration_ms=200000),
        current_track_uri=_SIG_URI,
        our_state=PlaybackState.PAUSED,
        in_settle_period=False,
    )
    pytest.assume(result == PlaybackSignal.NOTHING)


# --- Party-end time enforcement ---


def _long_song(uri="spotify:track:long", minutes=5) -> QueueItem:
    return QueueItem(
        track_name="Long",
        artist="A",
        album_art_url="",
        requester="",
        track_uri=uri,
        duration_ms=minutes * 60_000,
    )


def test_add_to_queue_returns_true_when_no_limit(service):
    ok = service.add_to_queue(_make_item())
    pytest.assume(ok is True)
    pytest.assume(len(service.get_queue()) == 1)


def test_add_to_queue_rejected_when_over_end_time(service, store):
    store.set_party_end_time(datetime.now() + timedelta(minutes=1))
    ok = service.add_to_queue(_long_song(minutes=5))
    pytest.assume(ok is False)
    pytest.assume(service.get_queue() == [])


def test_priority_add_rejected_when_over_end_time(service, store):
    # top=True must be gated too; position doesn't change the duration math.
    store.set_party_end_time(datetime.now() + timedelta(minutes=1))
    ok = service.add_to_queue(_long_song(minutes=5), top=True)
    pytest.assume(ok is False)
    pytest.assume(service.get_queue() == [])


def test_rejected_add_does_not_bump_version(service, store):
    store.set_party_end_time(datetime.now() + timedelta(minutes=1))
    before = service.version
    service.add_to_queue(_long_song(minutes=5))
    pytest.assume(service.version == before)


def test_add_within_end_time_succeeds(service, store):
    store.set_party_end_time(datetime.now() + timedelta(hours=2))
    ok = service.add_to_queue(_long_song(minutes=5))
    pytest.assume(ok is True)
    pytest.assume(len(service.get_queue()) == 1)


def test_set_and_clear_party_end(service):
    resolved = service.set_party_end("23:30")
    pytest.assume(resolved.hour == 23 and resolved.minute == 30)
    pytest.assume(service.get_party_end() == resolved)
    service.clear_party_end()
    pytest.assume(service.get_party_end() is None)


def test_adem_fill_capped_by_end_time(service, store):
    # Ademnood is 3.5 min each; a 10-min window fits 2 (7m), not a 3rd (10.5m).
    store.set_party_end_time(datetime.now() + timedelta(minutes=10))
    service.start_session("Party", "dev1", adem_mode=True)
    pytest.assume(len(service.get_queue()) == 2)


def test_adem_fill_unlimited_without_end_time(service):
    service.start_session("Party", "dev1", adem_mode=True)
    pytest.assume(len(service.get_queue()) == ADEM_MODE_QUEUE_SIZE)
