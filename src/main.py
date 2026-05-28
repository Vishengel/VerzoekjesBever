from nicegui import app, ui

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


def start_polling() -> None:
    svc = get_service()

    async def poll():
        svc.poll_currently_playing()

    ui.timer(3.0, poll)


# Import pages to register routes
from pages import audience, dj, startup  # noqa: E402, F401


def main():
    app.on_startup(start_polling)
    ui.run(title="VerzoekjesBever", favicon="🦫", dark=True, reload=False, show=False, port=8000)


if __name__ == "__main__":
    main()
