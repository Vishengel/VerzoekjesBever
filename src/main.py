import asyncio
import logging

from nicegui import app, background_tasks, ui
from spotipy.exceptions import SpotifyException

logger = logging.getLogger(__name__)

from config import CONFIG
from party_service import PartyService
from persistence import RequesterMap
from spotify_client import SpotifyClient

service: PartyService | None = None


def get_service() -> PartyService:
    global service
    if service is None:
        spotify = SpotifyClient()
        requester_map = RequesterMap(CONFIG.requester_map_path)
        service = PartyService(spotify=spotify, requester_map=requester_map)
    return service


async def poll_loop() -> None:
    svc = get_service()
    loop = asyncio.get_event_loop()
    logger.info("Polling started")
    while True:
        try:
            await loop.run_in_executor(None, svc.poll_currently_playing)
        except SpotifyException:
            logger.error("Polling error", exc_info=True)
        await asyncio.sleep(3.0)


# Import pages to register routes
from pages import audience, dj, startup  # noqa: E402, F401


@app.get("/debug")
def debug():
    svc = get_service()
    cp = svc.get_currently_playing()
    raw = svc.spotify.get_currently_playing_track()
    return {
        "playlist_id": svc.playlist_id,
        "version": svc.version,
        "currently_playing": cp.track_name if cp else None,
        "queue_length": len(svc.get_queue()),
        "spotify_raw": raw["name"] if raw else None,
        "spotify_is_playing": raw is not None,
    }


def main():
    # Trigger OAuth flow before starting web server so the token gets cached.
    # Spotipy's interactive auth starts its own HTTP server — can't do that inside a request handler.
    svc = get_service()
    svc.spotify.current_user()

    background_tasks.create_or_defer(poll_loop(), name='spotify-poll')
    ui.run(title="VerzoekjesBever", favicon="🦫", dark=True, reload=False, show=False, port=8000)


if __name__ == "__main__":
    main()
