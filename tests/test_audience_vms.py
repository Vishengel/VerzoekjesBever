import pytest

from models import QueueItem
from pages.audience import (
    PROMINENT_COUNT,
    AudienceRowVM,
    audience_row_vms,
    split_audience_vms,
)


def _item(uid, uri="spotify:track:x", req="", dur=60000):
    return QueueItem(
        track_name="T",
        artist="A",
        album_art_url="",
        requester=req,
        track_uri=uri,
        thumb_url="",
        duration_ms=dur,
        uid=uid,
    )


def test_positions_and_eta_accumulate():
    q = [_item("a", dur=60000), _item("b", dur=90000)]
    vms = audience_row_vms(q, window=30)
    pytest.assume(isinstance(vms[0], AudienceRowVM))
    pytest.assume([v.uid for v in vms] == ["a", "b"])
    pytest.assume(vms[0].position == 1 and vms[0].eta_ms == 0)
    pytest.assume(vms[1].position == 2 and vms[1].eta_ms == 60000)
    pytest.assume(vms[1].is_last is True and vms[0].is_last is False)


def test_window_truncates():
    q = [_item(str(i)) for i in range(40)]
    vms = audience_row_vms(q, window=30)
    pytest.assume(len(vms) == 30)
    pytest.assume(vms[-1].is_last is True)


def test_split_separates_prominent_and_scroll():
    q = [_item(str(i)) for i in range(10)]
    vms = audience_row_vms(q, window=30)
    prominent, scroll = split_audience_vms(vms)
    pytest.assume(
        [v.uid for v in prominent] == [str(i) for i in range(PROMINENT_COUNT)]
    )
    pytest.assume(
        [v.uid for v in scroll] == [str(i) for i in range(PROMINENT_COUNT, 10)]
    )
    pytest.assume(len(prominent) + len(scroll) == 10)


def test_split_at_prominent_count_has_no_scroll():
    q = [_item(str(i)) for i in range(PROMINENT_COUNT)]
    vms = audience_row_vms(q, window=30)
    prominent, scroll = split_audience_vms(vms)
    pytest.assume(len(prominent) == PROMINENT_COUNT)
    pytest.assume(scroll == [])


def test_split_one_more_than_prominent_has_single_scroll():
    q = [_item(str(i)) for i in range(PROMINENT_COUNT + 1)]
    vms = audience_row_vms(q, window=30)
    prominent, scroll = split_audience_vms(vms)
    pytest.assume(len(prominent) == PROMINENT_COUNT)
    pytest.assume([v.uid for v in scroll] == [str(PROMINENT_COUNT)])
