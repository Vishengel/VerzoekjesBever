import pytest

from config import Config


def test_audience_queue_window_defaults_to_30(monkeypatch):
    monkeypatch.delenv("AUDIENCE_QUEUE_WINDOW", raising=False)
    cfg = Config(spotipy_client_id="x", spotipy_client_secret="y", _env_file=None)
    pytest.assume(cfg.audience_queue_window == 30)


def test_audience_queue_window_reads_env(monkeypatch):
    monkeypatch.setenv("AUDIENCE_QUEUE_WINDOW", "12")
    cfg = Config(spotipy_client_id="x", spotipy_client_secret="y", _env_file=None)
    pytest.assume(cfg.audience_queue_window == 12)
