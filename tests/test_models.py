from models import QueueItem, PlaybackState
import pytest


def test_playback_state_values():
    pytest.assume(PlaybackState.IDLE.value == "idle")
    pytest.assume(PlaybackState.PLAYING.value == "playing")
    pytest.assume(PlaybackState.PAUSED.value == "paused")


def test_queue_item_creation():
    item = QueueItem(
        track_name="Dancing Queen",
        artist="ABBA",
        album_art_url="https://i.scdn.co/image/abc123",
        requester="Lisa",
        track_uri="spotify:track:0GjEhVFGZW8afUYGChu3Rr",
    )
    pytest.assume(item.track_name == "Dancing Queen")
    pytest.assume(item.artist == "ABBA")
    pytest.assume(item.requester == "Lisa")


def test_queue_item_from_spotify_track():
    spotify_track = {
        "name": "Mr. Brightside",
        "artists": [{"name": "The Killers"}],
        "album": {"images": [{"url": "https://i.scdn.co/image/xyz"}]},
        "uri": "spotify:track:003vvx7Niy0yvhvHt4a68B",
    }
    item = QueueItem.from_spotify_track(spotify_track, requester="Mark")
    pytest.assume(item.track_name == "Mr. Brightside")
    pytest.assume(item.artist == "The Killers")
    pytest.assume(item.album_art_url == "https://i.scdn.co/image/xyz")
    pytest.assume(item.requester == "Mark")
    pytest.assume(item.track_uri == "spotify:track:003vvx7Niy0yvhvHt4a68B")


def test_queue_item_to_dict():
    item = QueueItem(
        track_name="Dancing Queen",
        artist="ABBA",
        album_art_url="https://img.com/dq.jpg",
        requester="Lisa",
        track_uri="spotify:track:dq",
    )
    d = item.to_dict()
    pytest.assume(d == {
        "track_name": "Dancing Queen",
        "artist": "ABBA",
        "album_art_url": "https://img.com/dq.jpg",
        "track_uri": "spotify:track:dq",
        "requester": "Lisa",
    })


def test_queue_item_from_dict():
    d = {
        "track_name": "Dancing Queen",
        "artist": "ABBA",
        "album_art_url": "https://img.com/dq.jpg",
        "track_uri": "spotify:track:dq",
        "requester": "Lisa",
    }
    item = QueueItem.from_dict(d)
    pytest.assume(item.track_name == "Dancing Queen")
    pytest.assume(item.requester == "Lisa")


def test_queue_item_roundtrip():
    item = QueueItem(
        track_name="Song", artist="Art", album_art_url="", requester="X", track_uri="spotify:track:abc"
    )
    pytest.assume(QueueItem.from_dict(item.to_dict()) == item)


def test_queue_item_from_spotify_track_no_album_art():
    spotify_track = {
        "name": "Some Song",
        "artists": [{"name": "Artist"}],
        "album": {"images": []},
        "uri": "spotify:track:abc",
    }
    item = QueueItem.from_spotify_track(spotify_track, requester="Guest")
    pytest.assume(item.album_art_url == "")
