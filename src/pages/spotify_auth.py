import logging

from nicegui import ui

from deps import get_service

logger = logging.getLogger(__name__)


@ui.page("/auth/spotify/callback", title="Spotify Authorization", dark=True)
def spotify_callback(code: str = ""):
    svc = get_service()

    if not code:
        ui.navigate.to("/")
        return

    try:
        svc.handle_auth_callback(code)
        ui.navigate.to("/")
    except Exception:
        logger.exception("Spotify OAuth callback failed")
        with ui.column().classes("w-full max-w-md mx-auto mt-32 gap-6 items-center"):
            ui.label("Spotify Authorization Failed").classes(
                "text-2xl font-bold text-red-400"
            )
            ui.label(
                "Could not complete Spotify authorization. The code may have expired."
            ).classes("text-gray-400 text-center")
            ui.button(
                "Try Again",
                on_click=lambda: ui.navigate.to(svc.get_auth_url()),
            ).props("color=positive")
