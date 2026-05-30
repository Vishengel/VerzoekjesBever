from unittest.mock import MagicMock, patch

import pytest

from spotify_client import SpotifyClient


@pytest.fixture
def mock_spotipy():
    with (
        patch("spotify_client.Spotify") as mock_sp_cls,
        patch("spotify_client.SpotifyOAuth") as mock_oauth_cls,
        patch("spotify_client.CacheFileHandler"),
    ):
        mock_auth = MagicMock()
        mock_oauth_cls.return_value = mock_auth
        mock_sp = MagicMock()
        mock_sp_cls.return_value = mock_sp
        client = SpotifyClient()
        yield client, mock_auth, mock_sp


def test_is_authenticated_true(mock_spotipy):
    client, mock_auth, _ = mock_spotipy
    mock_auth.validate_token.return_value = {"access_token": "tok"}
    mock_auth.cache_handler.get_cached_token.return_value = {"access_token": "tok"}
    pytest.assume(client.is_authenticated() is True)


def test_is_authenticated_false_no_token(mock_spotipy):
    client, mock_auth, _ = mock_spotipy
    mock_auth.cache_handler.get_cached_token.return_value = None
    mock_auth.validate_token.return_value = None
    pytest.assume(client.is_authenticated() is False)


def test_get_auth_url(mock_spotipy):
    client, mock_auth, _ = mock_spotipy
    mock_auth.get_authorize_url.return_value = (
        "https://accounts.spotify.com/authorize?..."
    )
    url = client.get_auth_url()
    pytest.assume(url == "https://accounts.spotify.com/authorize?...")
    mock_auth.get_authorize_url.assert_called_once()


def test_handle_auth_callback(mock_spotipy):
    client, mock_auth, _ = mock_spotipy
    client.handle_auth_callback("test-code")
    mock_auth.get_access_token.assert_called_once_with(code="test-code", as_dict=False)


def test_open_browser_false():
    with (
        patch("spotify_client.Spotify"),
        patch("spotify_client.SpotifyOAuth") as mock_oauth_cls,
        patch("spotify_client.CacheFileHandler"),
    ):
        SpotifyClient()
        _, kwargs = mock_oauth_cls.call_args
        pytest.assume(kwargs.get("open_browser") is False)
