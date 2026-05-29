from nicegui import ui

from main import get_service


@ui.page("/setup", title="VerzoekjesBever — Setup", dark=True)
def setup_page():
    svc = get_service()
    spotify = svc.spotify

    playlists = spotify.fetch_session_playlists()
    playlist_options = {p["id"]: p["name"] for p in playlists}

    with ui.column().classes("w-full max-w-lg mx-auto mt-16 gap-6"):
        ui.label("🦫").classes("text-6xl text-center w-full")
        ui.label("VerzoekjesBever").classes("text-3xl font-bold text-center w-full")
        ui.label("Setup your party playlist").classes("text-gray-400 text-center w-full")

        ui.separator()

        ui.label("Create a new playlist").classes("text-lg font-semibold")
        with ui.row().classes("w-full gap-2"):
            new_name = ui.input("Playlist name", value="VerzoekjesBever — Party").classes("flex-grow")
            ui.button(
                "Create",
                on_click=lambda: start_with_new(new_name.value),
            ).props("color=positive")

        ui.separator()

        ui.label("Or resume a previous session").classes("text-lg font-semibold")
        selected = ui.select(
            options=playlist_options,
            label="Select playlist",
        ).classes("w-full")
        ui.button(
            "Use this playlist",
            on_click=lambda: start_with_existing(selected.value),
        ).props("color=primary").classes("w-full")

    def start_with_new(name: str):
        svc.start_session(playlist_id=None, playlist_name=name)
        ui.navigate.to("/dj")

    def start_with_existing(playlist_id: str):
        if not playlist_id:
            ui.notify("Pick a playlist first", type="warning")
            return
        svc.start_session(playlist_id=playlist_id)
        ui.navigate.to("/dj")
