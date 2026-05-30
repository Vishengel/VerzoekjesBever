from pathlib import Path

from models import QueueItem, PlaybackState
from persistence import QueueStore
import pytest


def _make_item(name: str = "Song", requester: str = "Lisa") -> QueueItem:
    return QueueItem(
        track_name=name,
        artist="Artist",
        album_art_url="",
        requester=requester,
        track_uri=f"spotify:track:{name}",
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
    pytest.assume(len(store.queue) == 1)
    pytest.assume(store.queue[0].track_name == "Song1")


def test_add_to_queue_assigns_fresh_uid(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    item = _make_item("Song1")
    original_uid = item.uid
    store.add_to_queue(item)
    pytest.assume(store.queue[0].uid != original_uid)


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
    uid = store.queue[0].uid
    store.remove_from_queue(uid)
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
    uid = store.queue[2].uid
    store.move_to_top(uid)
    pytest.assume(store.queue[0].track_name == "Song3")


def test_move_up(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    store.add_to_queue(_make_item("Song1"))
    store.add_to_queue(_make_item("Song2"))
    store.add_to_queue(_make_item("Song3"))
    uid = store.queue[1].uid
    store.move_up(uid)
    pytest.assume(store.queue[0].track_name == "Song2")
    pytest.assume(store.queue[1].track_name == "Song1")
    pytest.assume(store.queue[2].track_name == "Song3")


def test_move_up_first_item_noop(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    store.add_to_queue(_make_item("Song1"))
    store.add_to_queue(_make_item("Song2"))
    uid = store.queue[0].uid
    store.move_up(uid)
    pytest.assume(store.queue[0].track_name == "Song1")
    pytest.assume(store.queue[1].track_name == "Song2")


def test_move_up_unknown_uid_noop(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    store.add_to_queue(_make_item("Song1"))
    store.move_up("nonexistent")
    pytest.assume(len(store.queue) == 1)


def test_move_down(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    store.add_to_queue(_make_item("Song1"))
    store.add_to_queue(_make_item("Song2"))
    store.add_to_queue(_make_item("Song3"))
    uid = store.queue[1].uid
    store.move_down(uid)
    pytest.assume(store.queue[0].track_name == "Song1")
    pytest.assume(store.queue[1].track_name == "Song3")
    pytest.assume(store.queue[2].track_name == "Song2")


def test_move_down_last_item_noop(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    store.add_to_queue(_make_item("Song1"))
    store.add_to_queue(_make_item("Song2"))
    uid = store.queue[1].uid
    store.move_down(uid)
    pytest.assume(store.queue[0].track_name == "Song1")
    pytest.assume(store.queue[1].track_name == "Song2")


def test_move_down_unknown_uid_noop(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    store.add_to_queue(_make_item("Song1"))
    store.move_down("nonexistent")
    pytest.assume(len(store.queue) == 1)


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


def test_uid_survives_reload(tmp_path: Path):
    path = tmp_path / "session.json"
    store1 = QueueStore(path)
    store1.start_session("Party", "dev1")
    store1.add_to_queue(_make_item("Song1"))
    uid = store1.queue[0].uid

    store2 = QueueStore(path)
    pytest.assume(store2.queue[0].uid == uid)


def test_has_session(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    pytest.assume(not store.has_session)
    store.start_session("Party", "dev1")
    pytest.assume(store.has_session)


def test_update_requester_in_queue(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    store.add_to_queue(_make_item("Song1", requester="Typo"))
    uid = store.queue[0].uid
    store.update_requester(uid, "Corrected")
    pytest.assume(store.queue[0].requester == "Corrected")


def test_update_requester_currently_playing(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    item = _make_item("Song1", requester="Typo")
    store.set_currently_playing(item, PlaybackState.PLAYING)
    store.update_requester(item.uid, "Fixed")
    pytest.assume(store.currently_playing.requester == "Fixed")


def test_update_requester_persists(tmp_path: Path):
    path = tmp_path / "session.json"
    store = QueueStore(path)
    store.start_session("Party", "dev1")
    store.add_to_queue(_make_item("Song1", requester="Old"))
    uid = store.queue[0].uid
    store.update_requester(uid, "New")
    store2 = QueueStore(path)
    pytest.assume(store2.queue[0].requester == "New")


def test_file_created_on_mutation(tmp_path: Path):
    path = tmp_path / "session.json"
    store = QueueStore(path)
    pytest.assume(not path.exists())
    store.start_session("Party", "dev1")
    pytest.assume(path.exists())


def test_get_known_requesters(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    store.add_to_queue(_make_item("Song1", requester="Alice"))
    store.add_to_queue(_make_item("Song2", requester="Bob"))
    store.add_to_queue(_make_item("Song3", requester="Alice"))
    pytest.assume(store.get_known_requesters() == ["Alice", "Bob"])


def test_get_known_requesters_includes_currently_playing(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    store.set_currently_playing(
        _make_item("Now", requester="Charlie"), PlaybackState.PLAYING
    )
    store.add_to_queue(_make_item("Next", requester="Dana"))
    requesters = store.get_known_requesters()
    pytest.assume("Charlie" in requesters)
    pytest.assume("Dana" in requesters)


def test_get_known_requesters_excludes_empty(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    store.add_to_queue(_make_item("Song1", requester=""))
    store.add_to_queue(_make_item("Song2", requester="Alice"))
    pytest.assume(store.get_known_requesters() == ["Alice"])


def test_corrupt_file_starts_fresh(tmp_path: Path):
    path = tmp_path / "session.json"
    path.write_text("not valid json {{{")
    store = QueueStore(path)
    pytest.assume(store.session_name is None)
    pytest.assume(store.queue == [])


def test_atomic_write_produces_valid_file(tmp_path: Path):
    path = tmp_path / "session.json"
    store = QueueStore(path)
    store.start_session("Party", "dev1")
    store.add_to_queue(_make_item("Song1"))
    tmp_file = path.with_suffix(".tmp")
    pytest.assume(not tmp_file.exists())


def test_demo_queue_active_default_false(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    pytest.assume(store.demo_queue_active is False)


def test_demo_queue_active_persists(tmp_path: Path):
    path = tmp_path / "session.json"
    store1 = QueueStore(path)
    store1.start_session("Party", "dev1")
    store1.set_demo_queue_active(True)

    store2 = QueueStore(path)
    pytest.assume(store2.demo_queue_active is True)


def test_start_session_resets_demo_queue(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.set_demo_queue_active(True)
    store.start_session("Party", "dev1")
    pytest.assume(store.demo_queue_active is False)


def test_duplicate_track_uri_unique_uids(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    item = _make_item("Song1")
    store.add_to_queue(item)
    store.add_to_queue(item)
    pytest.assume(store.queue[0].uid != store.queue[1].uid)
    pytest.assume(store.queue[0].track_uri == store.queue[1].track_uri)


def test_remove_by_uid_only_removes_one_duplicate(tmp_path: Path):
    store = QueueStore(tmp_path / "session.json")
    store.start_session("Party", "dev1")
    item = _make_item("Song1")
    store.add_to_queue(item)
    store.add_to_queue(item)
    uid_to_remove = store.queue[0].uid
    store.remove_from_queue(uid_to_remove)
    pytest.assume(len(store.queue) == 1)
