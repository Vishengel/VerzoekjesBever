import json
from pathlib import Path

from models import QueueItem, PlaybackState
from persistence import QueueStore
import pytest


def _make_item(name: str = "Song", requester: str = "Lisa") -> QueueItem:
    return QueueItem(
        track_name=name, artist="Artist", album_art_url="", requester=requester, track_uri=f"spotify:track:{name}"
    )


def test_new_store_has_empty_state(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    pytest.assume(store.session_name is None)
    pytest.assume(store.device_id is None)
    pytest.assume(store.playback_state == PlaybackState.IDLE)
    pytest.assume(store.currently_playing is None)
    pytest.assume(store.queue == [])


def test_start_session(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("My Party", "device123")
    pytest.assume(store.session_name == "My Party")
    pytest.assume(store.device_id == "device123")
    pytest.assume(store.playback_state == PlaybackState.IDLE)


def test_add_to_queue_bottom(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    item = _make_item("Song1")
    store.add_to_queue(item)
    pytest.assume(store.queue == [item])


def test_add_to_queue_top(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    store.add_to_queue(_make_item("Song1"))
    store.add_to_queue(_make_item("Song2"), top=True)
    pytest.assume(store.queue[0].track_name == "Song2")
    pytest.assume(store.queue[1].track_name == "Song1")


def test_remove_from_queue(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    store.add_to_queue(_make_item("Song1"))
    store.remove_from_queue("spotify:track:Song1")
    pytest.assume(store.queue == [])


def test_pop_next(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    store.add_to_queue(_make_item("Song1"))
    store.add_to_queue(_make_item("Song2"))
    item = store.pop_next()
    pytest.assume(item.track_name == "Song1")
    pytest.assume(len(store.queue) == 1)


def test_pop_next_empty_returns_none(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    pytest.assume(store.pop_next() is None)


def test_set_currently_playing(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    item = _make_item("Now")
    store.set_currently_playing(item, PlaybackState.PLAYING)
    pytest.assume(store.currently_playing == item)
    pytest.assume(store.playback_state == PlaybackState.PLAYING)


def test_clear_currently_playing(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.set_currently_playing(_make_item("Now"), PlaybackState.PLAYING)
    store.clear_currently_playing()
    pytest.assume(store.currently_playing is None)
    pytest.assume(store.playback_state == PlaybackState.IDLE)


def test_set_device(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    store.set_device("dev2")
    pytest.assume(store.device_id == "dev2")


def test_set_playback_state(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.set_playback_state(PlaybackState.PAUSED)
    pytest.assume(store.playback_state == PlaybackState.PAUSED)


def test_move_to_top(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    store.add_to_queue(_make_item("Song1"))
    store.add_to_queue(_make_item("Song2"))
    store.add_to_queue(_make_item("Song3"))
    store.move_to_top("spotify:track:Song3")
    pytest.assume(store.queue[0].track_name == "Song3")


def test_persistence_survives_reload(tmp_path: Path):
    path = tmp_path / "session.json"
    store1 = QueueStore(path)
    store1.start_session("Party", "dev1")
    store1.add_to_queue(_make_item("Song1", "Lisa"))
    store1.set_currently_playing(_make_item("Current", "Mark"), PlaybackState.PLAYING)

    store2 = QueueStore(path)
    pytest.assume(store2.session_name == "Party")
    pytest.assume(store2.device_id == "dev1")
    pytest.assume(store2.queue[0].track_name == "Song1")
    pytest.assume(store2.queue[0].requester == "Lisa")
    pytest.assume(store2.currently_playing.track_name == "Current")
    pytest.assume(store2.playback_state == PlaybackState.PLAYING)


def test_has_session(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    pytest.assume(not store.has_session)
    store.start_session("Party", "dev1")
    pytest.assume(store.has_session)


def test_update_requester_in_queue(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    store.add_to_queue(_make_item("Song1", requester="Typo"))
    store.update_requester("spotify:track:Song1", "Corrected")
    pytest.assume(store.queue[0].requester == "Corrected")


def test_update_requester_currently_playing(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    item = _make_item("Song1", requester="Typo")
    store.set_currently_playing(item, PlaybackState.PLAYING)
    store.update_requester("spotify:track:Song1", "Fixed")
    pytest.assume(store.currently_playing.requester == "Fixed")


def test_update_requester_persists(tmp_path: Path):
    path = tmp_path / "session.json"
    store = QueueStore(path)
    store.start_session("Party", "dev1")
    store.add_to_queue(_make_item("Song1", requester="Old"))
    store.update_requester("spotify:track:Song1", "New")
    store2 = QueueStore(path)
    pytest.assume(store2.queue[0].requester == "New")


def test_file_created_on_mutation(tmp_path: Path):
    path = tmp_path / "session.json"
    store = QueueStore(path)
    pytest.assume(not path.exists())
    store.start_session("Party", "dev1")
    pytest.assume(path.exists())
