from nicegui import ui

from main import get_service
from models import QueueItem


@ui.page("/", title="VerzoekjesBever", dark=True)
def audience_page():
    svc = get_service()

    ui.add_head_html("""
    <style>
        body { background: linear-gradient(135deg, #0d0d1a 0%, #1a1a3e 100%) !important; }
    </style>
    """)

    with ui.column().classes("w-full max-w-3xl mx-auto p-8 gap-6"):
        with ui.column().classes("items-center gap-1"):
            ui.label("🦫").classes("text-5xl")
            ui.label("VERZOEKJESBEVER").classes("text-2xl font-extrabold tracking-wide text-white")
            ui.label("REQUEST PARTY").classes("text-xs tracking-[0.3em] text-green-400")

        if not svc.has_session:
            with ui.card().classes("w-full bg-gray-800 rounded-xl p-8 text-center"):
                ui.label("🦫").classes("text-4xl")
                ui.label("Waiting for DJ to start the party").classes("text-xl text-gray-400 mt-2")
                ui.label("Check back soon!").classes("text-gray-500")
            return

        # Request form
        with ui.card().classes("w-full bg-white/5 rounded-xl p-4"):
            ui.label("REQUEST A SONG").classes("text-xs tracking-[0.2em] text-gray-500")
            name_input = ui.input(placeholder="Your name...").classes("w-full")
            with ui.row().classes("w-full gap-2 mt-2"):
                search_input = ui.input(placeholder="Search song or artist...").classes("flex-grow")
                search_btn = ui.button("Search").props("color=primary dense")

            search_results = ui.column().classes("w-full gap-1 mt-2")

            def do_search():
                query = search_input.value.strip()
                if not query:
                    return
                results = svc.search_songs(query)
                search_results.clear()
                with search_results:
                    if not results:
                        ui.label("No results found").classes("text-gray-500 italic text-sm")
                        return
                    for track in results[:5]:
                        render_result(track)

            def render_result(item: QueueItem):
                with ui.row().classes("items-center gap-3 px-3 py-2 rounded-lg hover:bg-white/5"):
                    if item.album_art_url:
                        ui.image(item.album_art_url).classes("w-10 h-10 rounded")
                    with ui.column().classes("flex-grow gap-0"):
                        ui.label(item.track_name).classes("text-white text-sm font-semibold")
                        ui.label(item.artist).classes("text-gray-400 text-xs")
                    ui.button(
                        "Request",
                        on_click=lambda i=item: submit_request(i),
                    ).props("color=positive dense")

            def submit_request(item: QueueItem):
                name = name_input.value.strip() if name_input.value else ""
                if not name:
                    ui.notify("Enter your name first", type="warning")
                    return
                track_dict = {
                    "name": item.track_name,
                    "artists": [{"name": item.artist}],
                    "album": {"images": [{"url": item.album_art_url}] if item.album_art_url else []},
                    "uri": item.track_uri,
                }
                svc.add_song(track=track_dict, requester=name)
                ui.notify(f"Requested '{item.track_name}'!", type="positive")
                search_results.clear()
                search_input.value = ""

            search_btn.on_click(do_search)
            search_input.on("keydown.enter", do_search)

        @ui.refreshable
        def playlist_display():
            current = svc.get_currently_playing()

            if current:
                with ui.card().classes("w-full bg-green-600 rounded-xl p-5"):
                    ui.label("NOW PLAYING").classes("text-xs tracking-[0.2em] text-white/70")
                    with ui.row().classes("items-center gap-5 mt-2"):
                        if current.album_art_url:
                            ui.image(current.album_art_url).classes("w-20 h-20 rounded-lg")
                        with ui.column().classes("gap-0"):
                            ui.label(current.track_name).classes("text-2xl font-extrabold text-white")
                            ui.label(current.artist).classes("text-lg text-white/85")
                            if current.requester:
                                ui.label(f"🎤 Requested by {current.requester}").classes(
                                    "text-sm text-white/60 mt-1"
                                )
            else:
                with ui.card().classes("w-full bg-gray-800 rounded-xl p-8 text-center"):
                    ui.label("🦫").classes("text-4xl")
                    ui.label("No song playing yet").classes("text-xl text-gray-400 mt-2")
                    ui.label("Make a request!").classes("text-gray-500")

            queue = svc.get_queue()
            if queue:
                ui.label("UP NEXT").classes("text-xs tracking-[0.2em] text-gray-500 mt-4")
                with ui.card().classes("w-full bg-white/5 rounded-xl p-1"):
                    for i, item in enumerate(queue):
                        border = "border-b border-white/5" if i < len(queue) - 1 else ""
                        with ui.row().classes(f"items-center gap-3 px-4 py-3 {border}"):
                            ui.label(str(i + 1)).classes("text-green-400 font-extrabold text-lg w-7 text-center")
                            if item.album_art_url:
                                ui.image(item.album_art_url).classes("w-11 h-11 rounded-md")
                            with ui.column().classes("flex-grow gap-0"):
                                ui.label(item.track_name).classes("text-white font-semibold text-base")
                                ui.label(item.artist).classes("text-gray-400 text-sm")
                                if item.requester:
                                    ui.label(f"🎤 {item.requester}").classes("text-orange-400 text-xs mt-0.5")

        playlist_display()

        local_version = {"v": svc.version}

        def check_updates():
            if svc.version != local_version["v"]:
                local_version["v"] = svc.version
                playlist_display.refresh()

        ui.timer(1.0, check_updates)
