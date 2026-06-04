import asyncio
import hashlib
import logging
import os
from pathlib import Path

from log_config import setup_logging

setup_logging()

from nicegui import app, background_tasks, ui  # noqa: E402
from spotipy.exceptions import SpotifyException  # noqa: E402

from config import CONFIG  # noqa: E402
from deps import get_service  # noqa: E402
from pages import audience, benchmark, dj, login, spotify_auth, startup  # noqa: E402, F401

logger = logging.getLogger(__name__)

app.add_static_files("/static", str(Path(__file__).parent / "static"))


async def poll_loop() -> None:
    svc = get_service()
    loop = asyncio.get_running_loop()
    logger.info("Playback polling started")
    while True:
        try:
            if svc.is_authenticated():
                await loop.run_in_executor(None, svc.poll_playback)
        except SpotifyException:
            logger.error("Polling error", exc_info=True)
        # Single global loop (not per-client), so this is the only steady
        # Spotify call source: ~40 req/min, far under the rate limit. Lower
        # interval = snappier auto-advance at track end.
        await asyncio.sleep(1.5)


def main():
    reload = os.getenv("NICEGUI_RELOAD", "").lower() == "true"
    background_tasks.create_or_defer(poll_loop(), name="spotify-poll")

    storage_secret = hashlib.sha256(
        f"verzoekjesbever-{CONFIG.dj_password.get_secret_value()}".encode()
    ).hexdigest()

    ui.run(
        title="VerzoekjesBever",
        favicon="🦫",
        dark=True,
        reload=reload,
        show=False,
        host="0.0.0.0",
        port=8000,
        storage_secret=storage_secret,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
