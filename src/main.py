import asyncio
import logging

from nicegui import app, background_tasks, ui
from spotipy.exceptions import SpotifyException

from config import CONFIG
from party_service import PartyService
from persistence import QueueStore
from spotify_client import SpotifyClient

logger = logging.getLogger(__name__)

service: PartyService | None = None


def get_service() -> PartyService:
    global service
    if service is None:
        spotify = SpotifyClient()
        store = QueueStore(CONFIG.queue_store_path)
        service = PartyService(spotify=spotify, store=store)
    return service


async def poll_loop() -> None:
    svc = get_service()
    loop = asyncio.get_event_loop()
    logger.info("Playback polling started")
    while True:
        try:
            await loop.run_in_executor(None, svc.poll_playback)
        except SpotifyException:
            logger.error("Polling error", exc_info=True)
        await asyncio.sleep(3.0)


# Import pages to register routes
from pages import audience, dj, startup  # noqa: E402, F401


def main():
    svc = get_service()
    svc.spotify.current_user()

    background_tasks.create_or_defer(poll_loop(), name="spotify-poll")
    ui.run(title="VerzoekjesBever", favicon="🦫", dark=True, reload=False, show=False, port=8000)


if __name__ == "__main__":
    main()
