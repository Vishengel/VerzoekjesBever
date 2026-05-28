from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict

from base_config import BaseConfig


class Config(BaseConfig):
    package_root: Path = Path(__file__).parent

    spotipy_client_id: str
    spotipy_client_secret: SecretStr
    spotipy_redirect_uri: str

    model_config = SettingsConfigDict(
        env_file=BaseConfig.project_root / ".env", env_file_encoding="utf-8", env_ignore_empty=True, extra="ignore"
    )

    @property
    def requester_map_path(self) -> Path:
        return self.cache_dir / "requester_map.json"


CONFIG = Config()
