from dataclasses import replace

from nicegui import ui

from deps import get_service
from models import PlaybackState, QueueItem


@ui.page("/dj", title="VerzoekjesBever - DJ", dark=True)
def dj_page():
    svc = get_service()
    if not svc.has_session:
        ui.navigate.to("/")
        return
    DJPage(svc).build()


class DJPage:
    def __init__(self, svc):
        self.svc = svc
        self._requester_input: ui.input | None = None
        self._search_results: ui.column | None = None
        self._search_timer: ui.timer | None = None
        self._queue_display = None
        self._playback_controls = None

    def build(self):
        with ui.row().classes("w-full h-screen gap-0"):
            self._build_search_panel()
            self._build_queue_panel()

    def _build_search_panel(self):
        with ui.column().classes("w-1/2 p-6 gap-4 border-r border-gray-700 h-full"):
            self._build_header()
            self._build_requester_input()
            self._build_search_input()
            self._search_results = ui.column().classes(
                "w-full gap-2 overflow-auto flex-grow"
            )

    def _build_header(self):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("🦫 VerzoekjesBever — DJ").classes("text-2xl font-bold")
            with ui.row().classes("gap-2"):

                @ui.refreshable
                def beaver_toggle():
                    enabled = self.svc.beaver_enabled
                    ui.button(
                        "🦫 Beaver ON" if enabled else "🚫 Beaver OFF",
                        on_click=lambda: (
                            self.svc.set_beaver_enabled(not enabled),
                            beaver_toggle.refresh(),
                        ),
                    ).props(
                        f"{'color=positive' if enabled else 'color=negative'} dense"
                    )

                beaver_toggle()

                ui.button(
                    "Display",
                    on_click=lambda: ui.run_javascript(
                        "window.open('/display', '_blank')"
                    ),
                ).props("flat color=grey dense")
                ui.button(
                    "Settings",
                    on_click=lambda: ui.navigate.to("/"),
                ).props("flat color=grey dense")

    def _build_requester_input(self):
        with ui.card().classes("w-full bg-gray-900"):
            ui.label("Requester name").classes("text-sm text-gray-400")
            self._requester_input = ui.input(
                placeholder="Guest name...",
                autocomplete=self.svc.get_known_requesters(),
            ).classes("w-full")
            self._requester_input.on(
                "focus",
                lambda: self._requester_input.set_autocomplete(
                    self.svc.get_known_requesters()
                ),
            )

    def _build_search_input(self):
        search_input = ui.input(placeholder="Search song or artist...").classes(
            "w-full"
        )
        search_input.on("input", self._on_search_input)
        search_input.on("keydown.enter", lambda: self._do_search(search_input.value))

    def _on_search_input(self, e):
        query = e.sender.value
        if self._search_timer:
            self._search_timer.deactivate()
        if not query or len(query) < 2:
            self._search_results.clear()
            return
        self._search_timer = ui.timer(
            0.4, lambda q=query: self._do_search(q), once=True
        )

    def _do_search(self, query: str):
        if not query.strip():
            return
        results = self.svc.search_songs(query)
        self._search_results.clear()
        with self._search_results:
            if not results:
                ui.label("No results found").classes("text-gray-500 italic")
                return
            for item in results:
                self._render_search_result(item)

    def _render_search_result(self, item: QueueItem):
        with ui.card().classes("w-full bg-gray-800"):
            with ui.row().classes("items-center gap-3"):
                if item.album_art_url:
                    ui.image(item.album_art_url).classes("w-12 h-12 rounded")
                with ui.column().classes("flex-grow gap-0"):
                    ui.label(item.track_name).classes("font-semibold")
                    ui.label(item.artist).classes("text-sm text-gray-400")
                ui.button(
                    "+ Add",
                    on_click=lambda i=item: self._add_song(i, top=False),
                ).props("color=primary dense")
                ui.button(
                    "⬆ Top",
                    on_click=lambda i=item: self._add_song(i, top=True),
                ).props("color=warning dense")

    def _add_song(self, item: QueueItem, top: bool):
        requester = (
            self._requester_input.value.strip() if self._requester_input.value else ""
        )
        if not requester:
            ui.notify("Enter a requester name first", type="warning")
            return
        self.svc.add_to_queue(replace(item, requester=requester), top=top)
        position = "top" if top else "queue"
        ui.notify(
            f"Added '{item.track_name}' to {position} for {requester}", type="positive"
        )
        self._queue_display.refresh()

    def _build_queue_panel(self):
        with ui.column().classes("w-1/2 p-6 gap-4 h-full"):
            self._build_device_selector()

            @ui.refreshable
            def playback_controls():
                self._render_playback_controls()

            @ui.refreshable
            def queue_display():
                self._render_queue()

            self._playback_controls = playback_controls
            self._queue_display = queue_display

            playback_controls()
            queue_display()

            self._build_update_timer()

    def _build_device_selector(self):
        @ui.refreshable
        def device_selector():
            devices = self.svc.get_devices()
            options = {d["id"]: f"{d['name']} ({d['type']})" for d in devices}
            with ui.row().classes("w-full items-center gap-2"):
                current_device = (
                    self.svc.device_id if self.svc.device_id in options else None
                )
                ui.select(
                    options=options,
                    value=current_device,
                    label="Playback device",
                    on_change=lambda e: self.svc.set_device(e.value),
                ).classes("flex-grow")
                ui.button(icon="refresh", on_click=device_selector.refresh).props(
                    "flat round dense"
                )

        device_selector()

    def _refresh_all(self):
        self._queue_display.refresh()
        self._playback_controls.refresh()

    def _render_playback_controls(self):
        state = self.svc.playback_state
        with ui.row().classes("w-full justify-center gap-4"):
            if state == PlaybackState.PLAYING:
                ui.button(
                    "⏸ Pause", on_click=lambda: (self.svc.pause(), self._refresh_all())
                ).props("color=warning")
            elif state == PlaybackState.PAUSED:
                ui.button(
                    "▶ Resume",
                    on_click=lambda: (self.svc.resume(), self._refresh_all()),
                ).props("color=positive")
            ui.button(
                "⏭ Next", on_click=lambda: (self.svc.play_next(), self._refresh_all())
            ).props("color=primary")

    def _render_queue(self):
        current = self.svc.get_currently_playing()
        if current:
            self._render_now_playing(current)
        else:
            state_label = (
                "Paused"
                if self.svc.playback_state == PlaybackState.PAUSED
                else "Ready to play"
            )
            with ui.card().classes("w-full bg-gray-800 text-center p-6"):
                ui.label(state_label).classes("text-gray-400 text-lg")

        with ui.row().classes("w-full items-center justify-between mt-2"):
            ui.label("UP NEXT").classes("text-xs text-gray-400 tracking-widest")
            queue = self.svc.get_queue()
            if queue:
                ui.button("Clear queue", on_click=self._confirm_clear_queue).props(
                    "flat dense color=negative size=sm"
                )
        if not queue:
            ui.label("No songs in queue yet").classes("text-gray-500 italic")
        for i, item in enumerate(queue):
            self._render_queue_item(i, item, len(queue))

    def _render_now_playing(self, current: QueueItem):
        with ui.card().classes("w-full bg-gray-900 border-2 border-green-500"):
            ui.label("NOW PLAYING").classes("text-xs text-gray-400 tracking-widest")
            with ui.row().classes("items-center gap-4"):
                if current.album_art_url:
                    ui.image(current.album_art_url).classes("w-14 h-14 rounded")
                with ui.column().classes("flex-grow gap-0"):
                    ui.label(current.track_name).classes(
                        "text-lg font-bold text-green-400"
                    )
                    ui.label(current.artist).classes("text-gray-400")
                    with ui.row().classes("items-center gap-1"):
                        ui.label(
                            f"Requested by {current.requester}"
                            if current.requester
                            else "No requester"
                        ).classes("text-sm text-orange-400")
                        ui.button(
                            icon="edit",
                            on_click=lambda uid=current.uid,
                            name=current.requester: self._open_edit_requester(
                                uid, name
                            ),
                        ).props("flat round dense size=xs color=orange")

    def _render_queue_item(self, index: int, item: QueueItem, queue_len: int):
        with ui.card().classes("w-full bg-gray-900"):
            with ui.row().classes("items-center gap-3"):
                ui.label(str(index + 1)).classes(
                    "text-gray-500 font-bold w-6 text-center"
                )
                if item.album_art_url:
                    ui.image(item.album_art_url).classes("w-10 h-10 rounded")
                with ui.column().classes("flex-grow gap-0"):
                    ui.label(item.track_name).classes("font-semibold")
                    ui.label(item.artist).classes("text-sm text-gray-400")
                    if item.requester:
                        with ui.row().classes("items-center gap-1"):
                            ui.label(f"🎤 {item.requester}").classes(
                                "text-xs text-orange-400 mt-0.5"
                            )
                            ui.button(
                                icon="edit",
                                on_click=lambda uid=item.uid,
                                name=item.requester: self._open_edit_requester(
                                    uid, name
                                ),
                            ).props("flat round dense size=xs color=orange")
                with ui.column().classes("gap-0"):
                    up_btn = ui.button(
                        icon="arrow_upward",
                        on_click=lambda uid=item.uid: (
                            self.svc.move_up(uid),
                            self._queue_display.refresh(),
                        ),
                    ).props("flat round dense color=warning size=sm")
                    if index == 0:
                        up_btn.props(add="disable")
                    down_btn = ui.button(
                        icon="arrow_downward",
                        on_click=lambda uid=item.uid: (
                            self.svc.move_down(uid),
                            self._queue_display.refresh(),
                        ),
                    ).props("flat round dense color=warning size=sm")
                    if index == queue_len - 1:
                        down_btn.props(add="disable")
                ui.button(
                    icon="delete",
                    on_click=lambda uid=item.uid: (
                        self.svc.remove_from_queue(uid),
                        self._queue_display.refresh(),
                    ),
                ).props("flat round dense color=negative")

    def _build_update_timer(self):
        local_version = {"v": self.svc.version}

        def check_updates():
            if self.svc.version != local_version["v"]:
                local_version["v"] = self.svc.version
                self._refresh_all()

        ui.timer(1.0, check_updates)

    def _open_edit_requester(self, uid: str, current_name: str):
        with ui.dialog() as dialog, ui.card().classes("bg-gray-900 min-w-[300px]"):
            ui.label("Edit requester").classes("text-lg font-bold")
            name_input = ui.input(
                value=current_name,
                placeholder="Requester name...",
                autocomplete=self.svc.get_known_requesters(),
            ).classes("w-full")

            def save():
                self.svc.update_requester(uid, name_input.value.strip())
                self._queue_display.refresh()
                dialog.close()

            name_input.on("keydown.enter", save)
            with ui.row().classes("w-full justify-end gap-2 mt-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat color=grey")
                ui.button("Save", on_click=save).props("color=primary")
        dialog.open()

    def _confirm_clear_queue(self):
        count = len(self.svc.get_queue())
        with ui.dialog() as dialog, ui.card().classes("bg-gray-900 min-w-[300px]"):
            ui.label("Clear queue?").classes("text-lg font-bold")
            ui.label(f"This will remove all {count} songs from the queue.").classes(
                "text-gray-400"
            )

            def clear():
                self.svc.clear_queue()
                self._queue_display.refresh()
                dialog.close()
                ui.notify("Queue cleared", type="info")

            with ui.row().classes("w-full justify-end gap-2 mt-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat color=grey")
                ui.button("Clear all", on_click=clear).props("color=negative")
        dialog.open()
