from party_service import PartyService
from persistence import QueueStore, SkipTemplateStore
from spotify_client import SpotifyClient
from config import CONFIG

_service: PartyService | None = None


def get_service() -> PartyService:
    global _service
    if _service is None:
        spotify = SpotifyClient()
        store = QueueStore(CONFIG.queue_store_path)
        skip_templates = SkipTemplateStore(CONFIG.skip_templates_path)
        _service = PartyService(
            spotify=spotify, store=store, skip_templates=skip_templates
        )
    return _service


def reset_service() -> None:
    global _service
    _service = None
