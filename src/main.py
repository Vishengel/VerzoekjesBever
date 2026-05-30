import asyncio
import logging
import os
from pathlib import Path

from nicegui import app, background_tasks, ui
from spotipy.exceptions import SpotifyException

from deps import get_service
from pages import audience, dj, startup  # noqa: F401

logger = logging.getLogger(__name__)

app.add_static_files("/static", str(Path(__file__).parent / "static"))


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


def main():
    svc = get_service()
    svc.spotify.current_user()

    reload = os.getenv("NICEGUI_RELOAD", "").lower() == "true"
    background_tasks.create_or_defer(poll_loop(), name="spotify-poll")
    ui.run(
        title="VerzoekjesBever",
        favicon="🦫",
        dark=True,
        reload=reload,
        show=False,
        port=8000,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
