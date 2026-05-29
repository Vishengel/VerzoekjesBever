from nicegui import ui

from main import get_service


@ui.page("/", title="VerzoekjesBever", dark=True)
def audience_page():
    svc = get_service()

    ui.add_head_html("""
    <style>
        body { background: linear-gradient(135deg, #0d0d1a 0%, #1a1a3e 100%) !important; }
    </style>
    """)

    with ui.column().classes("w-full max-w-3xl mx-auto p-8 gap-6"):
        # Header
        with ui.column().classes("items-center gap-1"):
            ui.label("🦫").classes("text-5xl")
            ui.label("VERZOEKJESBEVER").classes("text-2xl font-extrabold tracking-wide text-white")
            ui.label("REQUEST PARTY").classes("text-xs tracking-[0.3em] text-green-400")

        @ui.refreshable
        def playlist_display():
            current = svc.get_currently_playing()

            # Now playing card
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

            # Queue
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
