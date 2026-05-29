from models import QueueItem, PlaybackState


def test_playback_state_values():
    assert PlaybackState.IDLE.value == "idle"
    assert PlaybackState.PLAYING.value == "playing"
    assert PlaybackState.PAUSED.value == "paused"


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


def test_queue_item_to_dict():
    item = QueueItem(
        track_name="Dancing Queen",
        artist="ABBA",
        album_art_url="https://img.com/dq.jpg",
        requester="Lisa",
        track_uri="spotify:track:dq",
    )
    d = item.to_dict()
    assert d == {
        "track_name": "Dancing Queen",
        "artist": "ABBA",
        "album_art_url": "https://img.com/dq.jpg",
        "track_uri": "spotify:track:dq",
        "requester": "Lisa",
    }


def test_queue_item_from_dict():
    d = {
        "track_name": "Dancing Queen",
        "artist": "ABBA",
        "album_art_url": "https://img.com/dq.jpg",
        "track_uri": "spotify:track:dq",
        "requester": "Lisa",
    }
    item = QueueItem.from_dict(d)
    assert item.track_name == "Dancing Queen"
    assert item.requester == "Lisa"


def test_queue_item_roundtrip():
    item = QueueItem(
        track_name="Song", artist="Art", album_art_url="", requester="X", track_uri="spotify:track:abc"
    )
    assert QueueItem.from_dict(item.to_dict()) == item


def test_queue_item_from_spotify_track_no_album_art():
    spotify_track = {
        "name": "Some Song",
        "artists": [{"name": "Artist"}],
        "album": {"images": []},
        "uri": "spotify:track:abc",
    }
    item = QueueItem.from_spotify_track(spotify_track, requester="Guest")
    assert item.album_art_url == ""
