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
