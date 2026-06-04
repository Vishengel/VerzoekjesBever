import pytest

from models import QueueItem
from pages.dj import DJRowVM, dj_row_vms


def _item(uid, req="", dur=60000):
    return QueueItem(
        track_name="T",
        artist="A",
        album_art_url="",
        requester=req,
        track_uri="spotify:track:x",
        thumb_url="",
        duration_ms=dur,
        uid=uid,
    )


def test_dj_vms_positions_eta_edges():
    q = [_item("a", dur=60000), _item("b", dur=90000), _item("c")]
    vms, total = dj_row_vms(q, filter_term="", window=50, show_all=False)
    pytest.assume(total == 3)
    pytest.assume(isinstance(vms[0], DJRowVM))
    pytest.assume([v.uid for v in vms] == ["a", "b", "c"])
    pytest.assume(vms[0].position == 1 and vms[0].eta_ms == 0)
    pytest.assume(vms[1].eta_ms == 60000)
    pytest.assume(vms[0].is_first is True and vms[0].is_last is False)
    pytest.assume(vms[2].is_last is True)


def test_dj_vms_filter_keeps_real_position():
    q = [_item("a"), _item("b", req="Zed"), _item("c")]
    vms, total = dj_row_vms(q, filter_term="zed", window=50, show_all=False)
    pytest.assume(total == 1)
    pytest.assume(len(vms) == 1 and vms[0].uid == "b" and vms[0].position == 2)
