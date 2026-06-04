import pytest

from models import QueueItem
from pages.audience import AudienceRowVM, audience_row_vms  # noqa: F401


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
    vms = audience_row_vms(q, window=30, pending_add_uri=None, pending_glow_uri=None)
    pytest.assume([v.uid for v in vms] == ["a", "b"])
    pytest.assume(vms[0].position == 1 and vms[0].eta_ms == 0)
    pytest.assume(vms[1].position == 2 and vms[1].eta_ms == 60000)
    pytest.assume(vms[1].is_last is True and vms[0].is_last is False)


def test_window_truncates():
    q = [_item(str(i)) for i in range(40)]
    vms = audience_row_vms(q, window=30, pending_add_uri=None, pending_glow_uri=None)
    pytest.assume(len(vms) == 30)
    pytest.assume(vms[-1].is_last is True)


def test_pending_flags_match_by_uri():
    q = [_item("a", uri="spotify:track:hit"), _item("b", uri="spotify:track:miss")]
    vms = audience_row_vms(
        q, window=30, pending_add_uri="spotify:track:hit", pending_glow_uri=None
    )
    pytest.assume(vms[0].is_target is True)
    pytest.assume(vms[1].is_target is False)


def test_is_target_wins_when_uri_matches_both():
    q = [_item("a", uri="spotify:track:hit")]
    vms = audience_row_vms(
        q,
        window=30,
        pending_add_uri="spotify:track:hit",
        pending_glow_uri="spotify:track:hit",
    )
    pytest.assume(vms[0].is_target is True)
    pytest.assume(vms[0].is_glow is False)
