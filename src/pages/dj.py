from nicegui import ui

from main import get_service
from models import QueueItem


@ui.page("/dj", title="VerzoekjesBever — DJ", dark=True)
def dj_page():
    svc = get_service()

    if svc.playlist_id is None:
        ui.navigate.to("/setup")
        return

    requester_input = None
    search_results_container = None

    with ui.row().classes("w-full h-screen gap-0"):
        # Left panel — Search
        with ui.column().classes("w-1/2 p-6 gap-4 border-r border-gray-700"):
            ui.label("🦫 VerzoekjesBever — DJ").classes("text-2xl font-bold")

            with ui.card().classes("w-full bg-gray-900"):
                ui.label("Requester name").classes("text-sm text-gray-400")
                requester_input = ui.input(placeholder="Guest name...").classes("w-full")

            with ui.row().classes("w-full gap-2"):
                search_input = ui.input(placeholder="Search song or artist...").classes("flex-grow")
                ui.button("Search", on_click=lambda: do_search(search_input.value)).props("color=primary")
                search_input.on("keydown.enter", lambda: do_search(search_input.value))

            search_results_container = ui.column().classes("w-full gap-2 overflow-auto")

        # Right panel — Queue
        with ui.column().classes("w-1/2 p-6 gap-4"):
            ui.label("Current Queue").classes("text-2xl font-bold")

            @ui.refreshable
            def queue_display():
                current = svc.get_currently_playing()
                if current:
                    with ui.card().classes("w-full bg-gray-900 border-2 border-green-500"):
                        ui.label("NOW PLAYING").classes("text-xs text-gray-400 tracking-widest")
                        with ui.row().classes("items-center gap-4"):
                            if current.album_art_url:
                                ui.image(current.album_art_url).classes("w-14 h-14 rounded")
                            with ui.column().classes("flex-grow gap-0"):
                                ui.label(current.track_name).classes("text-lg font-bold text-green-400")
                                ui.label(current.artist).classes("text-gray-400")
                                if current.requester:
                                    ui.label(f"Requested by {current.requester}").classes("text-sm text-orange-400")
                            ui.button(
                                "Remove",
                                on_click=lambda: remove_current(),
                            ).props("color=negative flat")

                ui.label("UP NEXT").classes("text-xs text-gray-400 tracking-widest mt-2")
                queue = svc.get_queue()
                if not queue:
                    ui.label("No songs in queue yet").classes("text-gray-500 italic")
                for i, item in enumerate(queue):
                    with ui.card().classes("w-full bg-gray-900"):
                        with ui.row().classes("items-center gap-3"):
                            ui.label(str(i + 1)).classes("text-gray-500 font-bold w-6 text-center")
                            if item.album_art_url:
                                ui.image(item.album_art_url).classes("w-10 h-10 rounded")
                            with ui.column().classes("flex-grow gap-0"):
                                ui.label(item.track_name).classes("font-semibold")
                                ui.label(item.artist).classes("text-sm text-gray-400")
                            if item.requester:
                                ui.label(item.requester).classes("text-sm text-orange-400")

            queue_display()

            local_version = {"v": svc.version}

            def check_updates():
                if svc.version != local_version["v"]:
                    local_version["v"] = svc.version
                    queue_display.refresh()

            ui.timer(1.0, check_updates)

    def do_search(query: str):
        if not query.strip():
            return
        results = svc.search_songs(query)
        search_results_container.clear()
        with search_results_container:
            if not results:
                ui.label("No results found").classes("text-gray-500 italic")
                return
            for track_result in results:
                render_search_result(track_result)

    def render_search_result(item: QueueItem):
        with ui.card().classes("w-full bg-gray-800"):
            with ui.row().classes("items-center gap-3"):
                if item.album_art_url:
                    ui.image(item.album_art_url).classes("w-12 h-12 rounded")
                with ui.column().classes("flex-grow gap-0"):
                    ui.label(item.track_name).classes("font-semibold")
                    ui.label(item.artist).classes("text-sm text-gray-400")
                ui.button(
                    "+ Add",
                    on_click=lambda i=item: add_song(i, top=False),
                ).props("color=primary dense")
                ui.button(
                    "⬆ Top",
                    on_click=lambda i=item: add_song(i, top=True),
                ).props("color=warning dense")

    def add_song(item: QueueItem, top: bool):
        requester = requester_input.value.strip() if requester_input.value else ""
        if not requester:
            ui.notify("Enter a requester name first", type="warning")
            return
        track_dict = {
            "name": item.track_name,
            "artists": [{"name": item.artist}],
            "album": {"images": [{"url": item.album_art_url}] if item.album_art_url else []},
            "uri": item.track_uri,
        }
        svc.add_song(track=track_dict, requester=requester, top=top)
        position = "top" if top else "queue"
        ui.notify(f"Added '{item.track_name}' to {position} for {requester}", type="positive")
        queue_display.refresh()

    def remove_current():
        svc.remove_currently_playing()
        ui.notify("Removed currently playing track", type="info")
        queue_display.refresh()
