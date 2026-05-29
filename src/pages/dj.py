from nicegui import ui

from main import get_service
from models import PlaybackState, QueueItem


@ui.page("/dj", title="VerzoekjesBever - DJ", dark=True)
def dj_page():
    svc = get_service()

    if not svc.has_session:
        ui.navigate.to("/")
        return

    requester_input = None
    search_results_container = None

    with ui.row().classes("w-full h-screen gap-0"):
        # Left panel — Search
        with ui.column().classes("w-1/2 p-6 gap-4 border-r border-gray-700 h-full"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label("🦫 VerzoekjesBever — DJ").classes("text-2xl font-bold")
                with ui.row().classes("gap-2"):
                    ui.button(
                        "Display",
                        on_click=lambda: ui.run_javascript("window.open('/display', '_blank')"),
                    ).props("flat color=grey dense")
                    ui.button(
                        "Settings",
                        on_click=lambda: ui.navigate.to("/setup"),
                    ).props("flat color=grey dense")

            with ui.card().classes("w-full bg-gray-900"):
                ui.label("Requester name").classes("text-sm text-gray-400")
                requester_input = ui.input(placeholder="Guest name...").classes("w-full")

            with ui.row().classes("w-full gap-2 items-center"):
                search_input = ui.input(placeholder="Search song or artist...").classes("flex-grow")
                ui.button("Search", on_click=lambda: do_search(search_input.value)).props("color=primary")
                search_input.on("keydown.enter", lambda: do_search(search_input.value))

            search_results_container = ui.column().classes("w-full gap-2 overflow-auto flex-grow")

        # Right panel - Queue + Controls
        with ui.column().classes("w-1/2 p-6 gap-4 h-full"):
            # Device switcher
            @ui.refreshable
            def device_selector():
                devices = svc.get_devices()
                options = {d["id"]: f"{d['name']} ({d['type']})" for d in devices}
                with ui.row().classes("w-full items-center gap-2"):
                    ui.select(
                        options=options,
                        value=svc.device_id,
                        label="Playback device",
                        on_change=lambda e: svc.set_device(e.value),
                    ).classes("flex-grow")
                    ui.button(icon="refresh", on_click=device_selector.refresh).props("flat round dense")

            device_selector()

            # Playback controls
            @ui.refreshable
            def playback_controls():
                state = svc.playback_state
                with ui.row().classes("w-full justify-center gap-4"):
                    if state == PlaybackState.PLAYING:
                        ui.button("⏸ Pause", on_click=lambda: (svc.pause(), playback_controls.refresh(), queue_display.refresh())).props("color=warning")
                    elif state == PlaybackState.PAUSED:
                        ui.button("▶ Resume", on_click=lambda: (svc.resume(), playback_controls.refresh(), queue_display.refresh())).props("color=positive")

                    ui.button("⏭ Next", on_click=lambda: (svc.play_next(), playback_controls.refresh(), queue_display.refresh())).props("color=primary")

            playback_controls()

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
                else:
                    state_label = "Paused" if svc.playback_state == PlaybackState.PAUSED else "Ready to play"
                    with ui.card().classes("w-full bg-gray-800 text-center p-6"):
                        ui.label(state_label).classes("text-gray-400 text-lg")

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
                                    ui.label(f"🎤 {item.requester}").classes("text-xs text-orange-400 mt-0.5")
                            ui.button(
                                icon="vertical_align_top",
                                on_click=lambda uri=item.track_uri: (svc.move_to_top(uri), queue_display.refresh()),
                            ).props("flat round dense color=warning")
                            ui.button(
                                icon="delete",
                                on_click=lambda uri=item.track_uri: (svc.remove_from_queue(uri), queue_display.refresh()),
                            ).props("flat round dense color=negative")

            queue_display()

            local_version = {"v": svc.version}

            def check_updates():
                if svc.version != local_version["v"]:
                    local_version["v"] = svc.version
                    queue_display.refresh()
                    playback_controls.refresh()

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
