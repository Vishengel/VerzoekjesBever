from models import (
    QueueItem,
    PlaybackState,
    search_queue,
    filter_queue_with_positions,
    format_queue_stats,
    select_album_art,
)
import pytest


def test_format_queue_stats_with_durations():
    queue = [
        QueueItem("A", "x", "", "g", "spotify:track:a", duration_ms=60_000),
        QueueItem("B", "x", "", "g", "spotify:track:b", duration_ms=60_000),
    ]
    stats = format_queue_stats(queue)
    pytest.assume("2 songs" in stats)
    pytest.assume("2m 0s remaining" in stats)


def test_format_queue_stats_without_durations_omits_time():
    queue = [QueueItem("A", "x", "", "g", "spotify:track:a")]
    stats = format_queue_stats(queue)
    pytest.assume("1 songs" in stats)
    pytest.assume("remaining" not in stats)


def _img(url, width):
    return {"url": url, "height": width, "width": width}


def test_select_album_art_picks_full_near_300_and_smallest_thumb():
    images = [_img("big", 640), _img("mid", 300), _img("tiny", 64)]
    full, thumb = select_album_art(images)
    pytest.assume(full == "mid")
    pytest.assume(thumb == "tiny")


def test_select_album_art_handles_unsorted_input():
    images = [_img("tiny", 64), _img("big", 640), _img("mid", 300)]
    full, thumb = select_album_art(images)
    pytest.assume(full == "mid")
    pytest.assume(thumb == "tiny")


def test_select_album_art_single_image():
    full, thumb = select_album_art([_img("only", 640)])
    pytest.assume(full == "only")
    pytest.assume(thumb == "only")


def test_select_album_art_empty():
    pytest.assume(select_album_art([]) == ("", ""))


def test_select_album_art_missing_widths_falls_back_to_largest():
    # No widths -> can't size; thumb = first, full = last (Spotify orders widest-first).
    images = [{"url": "a"}, {"url": "b"}, {"url": "c"}]
    full, thumb = select_album_art(images)
    pytest.assume(thumb == "a")
    pytest.assume(full == "c")


def test_select_album_art_no_image_above_threshold_uses_largest():
    images = [_img("a", 64), _img("b", 100)]
    full, thumb = select_album_art(images)
    pytest.assume(full == "b")
    pytest.assume(thumb == "a")


def test_from_spotify_track_sets_thumb_and_full():
    track = {
        "name": "Song",
        "artists": [{"name": "Artist"}],
        "album": {"images": [_img("big", 640), _img("mid", 300), _img("tiny", 64)]},
        "uri": "spotify:track:x",
    }
    item = QueueItem.from_spotify_track(track, requester="Guest")
    pytest.assume(item.album_art_url == "mid")
    pytest.assume(item.thumb_url == "tiny")


def test_from_dict_thumb_falls_back_to_full_for_legacy_data():
    legacy = {
        "track_name": "Old",
        "artist": "Artist",
        "album_art_url": "https://i.scdn.co/image/640",
        "track_uri": "spotify:track:old",
        "requester": "X",
    }
    item = QueueItem.from_dict(legacy)
    pytest.assume(item.thumb_url == "https://i.scdn.co/image/640")


def _item(track_name="Song", artist="Artist", requester="Guest", duration_ms=0):
    return QueueItem(
        track_name=track_name,
        artist=artist,
        album_art_url="",
        requester=requester,
        track_uri=f"spotify:track:{track_name}",
        duration_ms=duration_ms,
    )


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
    pytest.assume(d["track_name"] == "Dancing Queen")
    pytest.assume(d["artist"] == "ABBA")
    pytest.assume(d["album_art_url"] == "https://img.com/dq.jpg")
    pytest.assume(d["track_uri"] == "spotify:track:dq")
    pytest.assume(d["requester"] == "Lisa")
    pytest.assume("uid" in d)


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
        track_name="Song",
        artist="Art",
        album_art_url="",
        requester="X",
        track_uri="spotify:track:abc",
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


def test_search_queue_matches_each_field():
    queue = [
        _item(track_name="Africa", artist="Toto", requester="Gralg de Onsterfelijke"),
        _item(track_name="Hey Jude", artist="The Beatles", requester="Sam"),
    ]
    by_title = search_queue(queue, None, "africa")
    by_artist = search_queue(queue, None, "beatles")
    by_requester = search_queue(queue, None, "gralg")
    pytest.assume(len(by_title) == 1 and by_title[0].item.track_name == "Africa")
    pytest.assume(len(by_artist) == 1 and by_artist[0].item.artist == "The Beatles")
    pytest.assume(
        len(by_requester) == 1
        and by_requester[0].item.requester == "Gralg de Onsterfelijke"
    )


def test_search_queue_case_insensitive():
    queue = [_item(track_name="Bohemian Rhapsody", artist="Queen")]
    pytest.assume(len(search_queue(queue, None, "QUEEN")) == 1)
    pytest.assume(len(search_queue(queue, None, "bOhEmIaN")) == 1)


def test_search_queue_position_is_one_based():
    queue = [_item(track_name="A"), _item(track_name="B"), _item(track_name="C")]
    matches = search_queue(queue, None, "B")
    pytest.assume(len(matches) == 1)
    pytest.assume(matches[0].position == 2)
    pytest.assume(matches[0].now_playing is False)


def test_search_queue_eta_sums_songs_ahead():
    queue = [
        _item(track_name="A", duration_ms=180_000),
        _item(track_name="B", duration_ms=200_000),
        _item(track_name="C", duration_ms=240_000),
    ]
    # C is 3rd: ETA = duration of A + B = 380_000ms
    match = search_queue(queue, None, "C")[0]
    pytest.assume(match.eta_ms == 380_000)


def test_search_queue_currently_playing_match():
    current = _item(track_name="Now Playing Song", artist="Toto")
    queue = [_item(track_name="Other")]
    matches = search_queue(queue, current, "toto")
    pytest.assume(len(matches) == 1)
    pytest.assume(matches[0].now_playing is True)
    pytest.assume(matches[0].position == 0)
    pytest.assume(matches[0].eta_ms == 0)


def test_search_queue_empty_query():
    queue = [_item(track_name="Anything")]
    pytest.assume(search_queue(queue, None, "") == [])
    pytest.assume(search_queue(queue, None, "   ") == [])


def test_search_queue_no_match():
    queue = [
        _item(track_name="Africa", artist="Toto", requester="Gralg de Onsterfelijke")
    ]
    pytest.assume(search_queue(queue, None, "zzzz") == [])


def test_search_queue_multiple_matches_in_queue_order():
    queue = [
        _item(track_name="Toto Song A", duration_ms=100_000),
        _item(track_name="Other"),
        _item(track_name="Toto Song B", duration_ms=100_000),
    ]
    matches = search_queue(queue, None, "toto")
    pytest.assume([m.position for m in matches] == [1, 3])


def test_filter_queue_no_term_returns_all_with_positions():
    queue = [_item(track_name="A"), _item(track_name="B"), _item(track_name="C")]
    result = filter_queue_with_positions(queue, "")
    pytest.assume(len(result) == 3)
    pytest.assume([p.position for p in result] == [1, 2, 3])
    pytest.assume(result[0].item.track_name == "A")


def test_filter_queue_keeps_real_positions():
    # Matches at queue index 2 and 6 -> real positions 3 and 7.
    queue = [
        _item(track_name="Nope 1"),
        _item(track_name="Nope 2"),
        _item(track_name="Toto Hit", artist="Toto"),
        _item(track_name="Nope 3"),
        _item(track_name="Nope 4"),
        _item(track_name="Nope 5"),
        _item(track_name="Africa", artist="Toto"),
    ]
    result = filter_queue_with_positions(queue, "toto")
    pytest.assume([p.position for p in result] == [3, 7])
    pytest.assume(result[0].item.track_name == "Toto Hit")
    pytest.assume(result[1].item.track_name == "Africa")


def test_filter_queue_eta_sums_songs_ahead():
    queue = [
        _item(track_name="A", duration_ms=100_000),
        _item(track_name="B", duration_ms=200_000),
        _item(track_name="C", duration_ms=300_000),
    ]
    result = filter_queue_with_positions(queue, "")
    # ETA = sum of durations strictly ahead of each item.
    pytest.assume([p.eta_ms for p in result] == [0, 100_000, 300_000])


def test_filter_queue_case_insensitive_and_fields():
    queue = [
        _item(track_name="Africa", artist="Toto", requester="Gralg de Onsterfelijke"),
        _item(track_name="Hey Jude", artist="The Beatles", requester="Sam"),
    ]
    pytest.assume(len(filter_queue_with_positions(queue, "AFRICA")) == 1)
    pytest.assume(len(filter_queue_with_positions(queue, "beatles")) == 1)
    by_requester = filter_queue_with_positions(queue, "gralg")
    pytest.assume(len(by_requester) == 1 and by_requester[0].position == 1)


def test_filter_queue_no_match():
    queue = [_item(track_name="Africa", artist="Toto")]
    pytest.assume(filter_queue_with_positions(queue, "zzzz") == [])


def test_filter_queue_whitespace_term_returns_all():
    queue = [_item(track_name="A"), _item(track_name="B")]
    pytest.assume(len(filter_queue_with_positions(queue, "   ")) == 2)
