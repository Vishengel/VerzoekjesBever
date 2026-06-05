from pathlib import Path
from typing import ClassVar

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    project_root: ClassVar[Path] = Path(__file__).parent.parent
    cache_dir: ClassVar[Path] = project_root / "cache"

    spotipy_client_id: str
    spotipy_client_secret: SecretStr
    spotipy_redirect_uri: str = "http://127.0.0.1:8000/auth/spotify/callback"

    dj_password: SecretStr = SecretStr("")

    queue_store_path: Path = project_root / "data" / "session.json"
    # Shame-message templates live outside the session: starting a fresh
    # session (or losing the session file) must not wipe the DJ's messages.
    shame_templates_path: Path = project_root / "data" / "shame_templates.json"

    # Seconds between Spotify playback polls. Single global loop, so this is
    # the only steady API call source regardless of audience size; lower =
    # snappier auto-advance at track end.
    playback_poll_interval_s: float = 1.5

    # Max queue rows the audience billboard materialises (prominent + scrolling
    # combined). Caps DOM/memory so large queues stay smooth; the scroll loop
    # covers this slice and a "+ N more" tail rides at its end.
    audience_queue_window: int = 30

    model_config = SettingsConfigDict(
        env_file=project_root / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
    )


CONFIG = Config()
