from party_service import PartyService
from persistence import QueueStore
from spotify_client import SpotifyClient
from config import CONFIG

_service: PartyService | None = None


def get_service() -> PartyService:
    global _service
    if _service is None:
        spotify = SpotifyClient()
        store = QueueStore(CONFIG.queue_store_path)
        _service = PartyService(spotify=spotify, store=store)
    return _service
