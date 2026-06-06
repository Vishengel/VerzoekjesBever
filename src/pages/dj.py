from dataclasses import dataclass, replace
from datetime import datetime

from nicegui import app, ui

from config import CONFIG
from deps import get_service
from keyed_list import KeyedList
from models import (
    ANONYMOUS_REQUESTER,
    PlaybackState,
    QueueItem,
    filter_queue_with_positions,
    format_clock_eta,
    format_queue_stats,
)
from party_service import PartyService

DJ_QUEUE_WINDOW = 50
_END_TIME_FMT = "%a %b %d, %H:%M"


@dataclass(frozen=True)
class DJRowVM:
    uid: str
    track_name: str
    artist: str
    requester: str
    position: int  # 1-based real queue position
    eta_ms: int
    is_first: bool  # disables up + top buttons
    is_last: bool  # disables down button


def dj_row_vms(
    queue: list,
    *,
    filter_term: str,
    window: int,
    show_all: bool,
) -> tuple[list[DJRowVM], int]:
    """Pure view-models for the DJ queue rows (filtered + windowed, with ETA).

    Returns ``(vms, filtered_count)`` where ``filtered_count`` is the total number
    of items matching *filter_term* (before windowing).

    ``is_first`` is keyed to the row's *real* queue position (position == 1), so
    button-enabling matches the unfiltered queue, not the visible slice.
    """
    filtered = filter_queue_with_positions(queue, filter_term)
    filtered_count = len(filtered)
    visible = filtered if (show_all or filtered_count <= window) else filtered[:window]
    last_real = len(queue)
    return (
        [
            DJRowVM(
                uid=p.item.uid,
                track_name=p.item.track_name,
                artist=p.item.artist,
                requester=p.item.requester or "",
                position=p.position,
                eta_ms=p.eta_ms,
                is_first=p.position == 1,
                is_last=p.position == last_real,
            )
            for p in visible
        ],
        filtered_count,
    )


@dataclass
class _DJRow:
    root: ui.card
    pos: ui.label
    eta: ui.label
    requester_row: ui.row
    requester: ui.label
    up: ui.button
    down: ui.button
    top: ui.button
    is_first: bool = False
    is_last: bool = False


@ui.page("/dj", title="VerzoekjesBever - DJ", dark=True)
def dj_page():
    if CONFIG.dj_password.get_secret_value() and not app.storage.user.get(
        "authenticated"
    ):
        ui.navigate.to("/login")
        return
    svc = get_service()
    if not svc.has_session:
        ui.navigate.to("/")
        return
    DJPage(svc).build()


class DJPage:
    def __init__(self, svc: PartyService):
        self.svc = svc
        self._requester_input: ui.input | None = None
        self._search_results: ui.column | None = None
        self._search_timer: ui.timer | None = None
        self._playback_controls = None
        self._queue_filter: str = ""
        self._show_all_queue: bool = False
        self._np_container: ui.column | None = None
        self._np_sig: object = object()  # sentinel: forces first now-playing render
        self._stats_label: ui.label | None = None
        self._clear_btn: ui.button | None = None
        self._empty_label: ui.label | None = None
        self._no_match_label: ui.label | None = None
        self._list_container: ui.column | None = None
        self._queue_list: KeyedList | None = None
        self._more_btn: ui.button | None = None
        self._more_mode: str | None = None  # tracks Show-all/Show-less button state

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
            with ui.row().classes("items-center gap-2"):
                ui.image("/static/beaver.svg").classes("w-8 h-8")
                ui.label("VerzoekjesBever - DJ").classes("text-2xl font-bold")
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

                @ui.refreshable
                def qr_toggle():
                    enabled = self.svc.show_qr_code
                    ui.button(
                        "📱 QR ON" if enabled else "📱 QR OFF",
                        on_click=lambda: (
                            self.svc.set_show_qr_code(not enabled),
                            qr_toggle.refresh(),
                        ),
                    ).props(
                        f"{'color=positive' if enabled else 'color=negative'} dense"
                    )

                qr_toggle()

                @ui.refreshable
                def end_time_control():
                    end = self.svc.get_party_end()

                    def _apply(value: str):
                        val = (value or "").strip()
                        if not val:
                            return
                        try:
                            resolved = self.svc.set_party_end(val)
                        except (ValueError, TypeError):
                            ui.notify("Use HH:MM (e.g. 02:00)", type="negative")
                            return
                        ui.notify(
                            f"Party ends {resolved.strftime(_END_TIME_FMT)}",
                            type="positive",
                        )
                        end_time_control.refresh()
                        self._render_queue()

                    with ui.row().classes("items-center gap-1"):
                        clock_btn = ui.button(icon="schedule").props(
                            "flat round dense color=grey"
                        )
                        clock_btn.tooltip("Set party end time")
                        with clock_btn, ui.menu() as menu:
                            picker = ui.time(
                                value=end.strftime("%H:%M") if end else None
                            )
                            with ui.row().classes("justify-end gap-1 w-full px-2 pb-2"):
                                if end:
                                    ui.button(
                                        "Clear",
                                        on_click=lambda: (
                                            self.svc.clear_party_end(),
                                            menu.close(),
                                            end_time_control.refresh(),
                                            self._render_queue(),
                                        ),
                                    ).props("flat dense color=grey")
                                ui.button(
                                    "Set",
                                    on_click=lambda: (
                                        _apply(picker.value),
                                        menu.close(),
                                    ),
                                ).props("flat dense color=positive")
                        if end:
                            ui.label(f"Ends {end.strftime(_END_TIME_FMT)}").classes(
                                "text-xs text-green-400"
                            )

                end_time_control()

                @ui.refreshable
                def shame_msg_toggle():
                    enabled = self.svc.shame_messages_enabled
                    ui.button(
                        "💬 Shame ON" if enabled else "🤐 Shame OFF",
                        on_click=lambda: (
                            self.svc.set_shame_messages_enabled(not enabled),
                            shame_msg_toggle.refresh(),
                        ),
                    ).props(
                        f"{'color=positive' if enabled else 'color=negative'} dense"
                    )

                shame_msg_toggle()

                ui.button(
                    icon="edit_note",
                    on_click=self._open_shame_messages,
                ).props("flat round dense color=grey").tooltip("Edit shame messages")

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
        search_input = ui.input(
            placeholder="Search song or artist...",
            on_change=self._on_search_input,
        ).classes("w-full")
        search_input.on("keydown.enter", lambda: self._do_search(search_input.value))

    def _on_search_input(self, e):
        query = e.value
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
        fits = self.svc.can_fit(item.duration_ms)
        with ui.card().classes("w-full bg-gray-800"):
            with ui.row().classes("items-center gap-3 w-full"):
                if item.thumb_url:
                    ui.image(item.thumb_url).classes("w-12 h-12 rounded")
                with ui.column().classes("flex-grow gap-0"):
                    ui.label(item.track_name).classes("font-semibold")
                    ui.label(item.artist).classes("text-sm text-gray-400")
                if not fits:
                    ui.label("⛔ after end time").classes("text-xs text-red-400")
                add_btn = ui.button(
                    "+ Add",
                    on_click=lambda i=item: self._add_song(i, top=False),
                ).props("color=primary dense")
                top_btn = ui.button(
                    "⬆ Top",
                    on_click=lambda i=item: self._add_song(i, top=True),
                ).props("color=warning dense")
                if not fits:
                    add_btn.props(add="disable")
                    top_btn.props(add="disable")

    def _add_song(self, item: QueueItem, top: bool):
        requester = (
            self._requester_input.value.strip() if self._requester_input.value else ""
        )
        if not requester:
            requester = ANONYMOUS_REQUESTER
        added = self.svc.add_to_queue(replace(item, requester=requester), top=top)
        if not added:
            ui.notify(
                "Party ends before this song would finish — not added",
                type="negative",
            )
            return
        position = "top" if top else "queue"
        ui.notify(
            f"Added '{item.track_name}' to {position} for {requester}", type="positive"
        )
        self._render_queue()

    def _build_queue_panel(self):
        with ui.column().classes("w-1/2 p-6 gap-4 h-full"):
            self._build_device_selector()

            @ui.refreshable
            def playback_controls():
                self._render_playback_controls()

            self._playback_controls = playback_controls
            playback_controls()

            ui.input(
                placeholder="Filter by requester, title, or artist...",
                value=self._queue_filter,
                on_change=self._on_queue_filter,
            ).classes("w-full").props("dense clearable outlined")

            self._np_container = ui.column().classes("w-full gap-0")

            with ui.row().classes("w-full items-center justify-between mt-2"):
                with ui.row().classes("items-center gap-3"):
                    ui.label("UP NEXT").classes("text-xs text-gray-400 tracking-widest")
                    self._stats_label = ui.label("").classes(
                        "text-sm font-medium text-green-400/80 "
                        "bg-green-900/30 rounded-full px-3 py-0.5"
                    )
                self._clear_btn = ui.button(
                    "Clear queue", on_click=self._confirm_clear_queue
                ).props("flat dense color=negative size=sm")

            self._empty_label = ui.label("No songs in queue yet").classes(
                "text-gray-500 italic"
            )
            self._no_match_label = ui.label("No matching songs").classes(
                "text-gray-500 italic"
            )
            self._list_container = ui.column().classes("w-full gap-2")
            self._queue_list = KeyedList(
                self._list_container,
                key=lambda vm: vm.uid,
                build=self._build_dj_row,
                patch=self._patch_dj_row,
            )
            self._more_btn = (
                ui.button("", on_click=self._toggle_show_all_queue)
                .props("flat dense color=primary size=sm")
                .classes("w-full mt-1")
            )

            self._render_all()
            self._build_update_timer()

    def _render_all(self):
        self._render_now_playing()
        self._render_queue()

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
        self._render_all()
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

    def _render_now_playing(self):
        current = self.svc.get_currently_playing()
        sig = (
            (current.uid, current.requester)
            if current
            else ("paused" if self.svc.playback_state == PlaybackState.PAUSED else None)
        )
        if sig == self._np_sig:
            return
        self._np_sig = sig
        self._np_container.clear()
        with self._np_container:
            if current:
                self._render_now_playing_card(current)
            else:
                state_label = (
                    "Paused"
                    if self.svc.playback_state == PlaybackState.PAUSED
                    else "Ready to play"
                )
                with ui.card().classes("w-full bg-gray-800 text-center p-6"):
                    ui.label(state_label).classes("text-gray-400 text-lg")

    def _render_now_playing_card(self, current: QueueItem):
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
                            on_click=lambda uid=current.uid: self._open_edit_requester(
                                uid
                            ),
                        ).props("flat round dense size=xs color=orange")

    def _render_queue(self):
        queue = self.svc.get_queue()
        self._stats_label.set_text(
            format_queue_stats(
                queue, self.svc.get_current_remaining_ms(), datetime.now()
            )
            if queue
            else ""
        )
        over = self.svc.queue_overshoots_end()
        self._stats_label.classes(
            remove="text-green-400/80 bg-green-900/30 text-red-300 bg-red-900/40",
            add=(
                "text-red-300 bg-red-900/40"
                if over
                else "text-green-400/80 bg-green-900/30"
            ),
        )
        self._clear_btn.set_visibility(bool(queue))
        self._empty_label.set_visibility(not queue)

        vms, filtered_count = dj_row_vms(
            queue,
            filter_term=self._queue_filter,
            window=DJ_QUEUE_WINDOW,
            show_all=self._show_all_queue,
        )
        self._no_match_label.set_visibility(
            bool(self._queue_filter) and filtered_count == 0
        )
        self._queue_list.reconcile(vms)

        hidden = filtered_count - len(vms)
        if hidden > 0:
            self._more_btn.set_text(
                f"Show all {filtered_count} songs (+{hidden} hidden)"
            )
            if self._more_mode != "more":
                self._more_btn.props(remove="color=grey", add="color=primary")
                self._more_mode = "more"
            self._more_btn.set_visibility(True)
        elif self._show_all_queue and filtered_count > DJ_QUEUE_WINDOW:
            self._more_btn.set_text("Show less")
            if self._more_mode != "less":
                self._more_btn.props(remove="color=primary", add="color=grey")
                self._more_mode = "less"
            self._more_btn.set_visibility(True)
        else:
            self._more_btn.set_visibility(False)
            self._more_mode = None

    def _build_dj_row(self, vm: DJRowVM) -> _DJRow:
        card = ui.card().classes("w-full bg-gray-900")
        with card:
            with ui.row().classes("items-center gap-3 w-full"):
                with ui.column().classes("items-center gap-0 w-12"):
                    pos = ui.label(str(vm.position)).classes(
                        "text-gray-500 font-bold text-center"
                    )
                    eta = ui.label("").classes(
                        "text-[10px] text-green-400/70 text-center leading-tight"
                    )
                with ui.column().classes("flex-grow gap-0"):
                    ui.label(vm.track_name).classes("font-semibold")
                    ui.label(vm.artist).classes("text-sm text-gray-400")
                    requester_row = ui.row().classes("items-center gap-1")
                    with requester_row:
                        requester = ui.label("").classes(
                            "text-xs text-orange-400 mt-0.5"
                        )
                        ui.button(
                            icon="edit",
                            on_click=lambda uid=vm.uid: self._open_edit_requester(uid),
                        ).props("flat round dense size=xs color=orange")
                with ui.column().classes("gap-0"):
                    top = ui.button(
                        icon="vertical_align_top",
                        on_click=lambda uid=vm.uid: (
                            self.svc.move_to_top(uid),
                            self._render_queue(),
                        ),
                    ).props("flat round dense color=orange size=sm")
                    up = ui.button(
                        icon="arrow_upward",
                        on_click=lambda uid=vm.uid: (
                            self.svc.move_up(uid),
                            self._render_queue(),
                        ),
                    ).props("flat round dense color=warning size=sm")
                    down = ui.button(
                        icon="arrow_downward",
                        on_click=lambda uid=vm.uid: (
                            self.svc.move_down(uid),
                            self._render_queue(),
                        ),
                    ).props("flat round dense color=warning size=sm")
                with ui.column().classes("gap-0"):
                    ui.button(
                        icon="delete",
                        on_click=lambda uid=vm.uid: (
                            self.svc.remove_from_queue(uid),
                            self._render_queue(),
                        ),
                    ).props("outline round dense color=negative size=sm").tooltip(
                        "Delete (quiet)"
                    )
                    ui.button(
                        icon="paid",
                        on_click=lambda uid=vm.uid: self._open_shame_delete(uid),
                    ).props("flat round dense color=negative size=sm").tooltip(
                        "Shame delete (paid)"
                    )
        handle = _DJRow(
            root=card,
            pos=pos,
            eta=eta,
            requester_row=requester_row,
            requester=requester,
            up=up,
            down=down,
            top=top,
        )
        self._patch_dj_row(handle, vm)
        return handle

    def _patch_dj_row(self, h: _DJRow, vm: DJRowVM):
        if h.pos.text != str(vm.position):
            h.pos.set_text(str(vm.position))
        if vm.eta_ms == 0:
            eta_text = "Up next!"
        else:
            clock = format_clock_eta(
                self.svc.get_current_remaining_ms() + vm.eta_ms, datetime.now()
            )
            eta_text = f"ETA {clock}"
        if h.eta.text != eta_text:
            h.eta.set_text(eta_text)
        req_text = f"🎤 {vm.requester}" if vm.requester else ""
        if h.requester.text != req_text:
            h.requester.set_text(req_text)
        h.requester_row.set_visibility(bool(vm.requester))
        if h.is_first != vm.is_first:
            h.is_first = vm.is_first
            for btn in (h.up, h.top):
                if vm.is_first:
                    btn.props(add="disable")
                else:
                    btn.props(remove="disable")
        if h.is_last != vm.is_last:
            h.is_last = vm.is_last
            if vm.is_last:
                h.down.props(add="disable")
            else:
                h.down.props(remove="disable")

    def _on_queue_filter(self, e):
        self._queue_filter = e.value or ""
        self._render_queue()

    def _toggle_show_all_queue(self):
        self._show_all_queue = not self._show_all_queue
        self._render_queue()

    def _build_update_timer(self):
        local_version = {"v": self.svc.version}

        def check_updates():
            if self.svc.version == local_version["v"]:
                return
            local_version["v"] = self.svc.version
            self._playback_controls.refresh()
            self._render_all()

        ui.timer(1.0, check_updates)

    def _open_shame_messages(self):
        with ui.dialog() as dialog, ui.card().classes("bg-gray-900 min-w-[360px]"):
            ui.label("💬 Shame messages").classes("text-lg font-bold")

            @ui.refreshable
            def template_list():
                templates = self.svc.get_shame_templates()
                if not templates:
                    ui.label(
                        "No shame messages. Shame deletes happen silently."
                    ).classes("text-gray-500 italic text-sm")
                for tpl in templates:
                    with ui.row().classes("w-full items-center gap-2"):
                        ui.label(tpl.text).classes("flex-grow text-sm")
                        ui.button(
                            icon="delete",
                            on_click=lambda uid=tpl.uid: (
                                self.svc.remove_shame_template(uid),
                                template_list.refresh(),
                            ),
                        ).props("flat round dense color=negative size=sm")

            template_list()

            new_input = ui.input(
                placeholder="New message: use {victim} {skipper} {artist} {song}",
            ).classes("w-full")

            def add_template():
                text = new_input.value.strip() if new_input.value else ""
                if not text:
                    return
                self.svc.add_shame_template(text)
                new_input.set_value("")
                template_list.refresh()

            new_input.on("keydown.enter", add_template)

            def reset_defaults():
                self.svc.reset_shame_templates()
                template_list.refresh()
                ui.notify("Shame messages reset to default", type="info")

            with ui.row().classes("w-full justify-between items-center gap-2 mt-2"):
                ui.button("Reset to default", on_click=reset_defaults).props(
                    "flat color=warning dense"
                )
                with ui.row().classes("gap-2"):
                    ui.button("Add message", on_click=add_template).props(
                        "color=primary dense"
                    )
                    ui.button("Close", on_click=dialog.close).props("flat color=grey")
        dialog.open()

    def _open_edit_requester(self, uid: str):
        current_name = self.svc.get_requester(uid)
        with ui.dialog() as dialog, ui.card().classes("bg-gray-900 min-w-[300px]"):
            ui.label("Edit requester").classes("text-lg font-bold")
            name_input = ui.input(
                value=current_name,
                placeholder="Requester name...",
                autocomplete=self.svc.get_known_requesters(),
            ).classes("w-full")

            def save():
                self.svc.update_requester(uid, name_input.value.strip())
                self._render_queue()
                self._render_now_playing()
                dialog.close()

            name_input.on("keydown.enter", save)
            with ui.row().classes("w-full justify-end gap-2 mt-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat color=grey")
                ui.button("Save", on_click=save).props("color=primary")
        dialog.open()

    def _open_shame_delete(self, uid: str):
        item = next((q for q in self.svc.get_queue() if q.uid == uid), None)
        if item is None:
            return
        requester = item.requester or "no requester"
        with ui.dialog() as dialog, ui.card().classes("bg-gray-900 min-w-[320px]"):
            ui.label("💰 Shame delete").classes("text-lg font-bold")
            ui.label(
                f"Delete: {item.track_name} – {item.artist} (requested by {requester})"
            ).classes("text-sm text-gray-400")
            name_input = ui.input(
                placeholder="Who paid? (optional)",
                autocomplete=self.svc.get_known_requesters(),
            ).classes("w-full")

            def confirm():
                skipper = name_input.value.strip() if name_input.value else ""
                self.svc.shame_delete(uid, skipper)
                self._render_queue()
                dialog.close()

            name_input.on("keydown.enter", confirm)
            with ui.row().classes("w-full justify-end gap-2 mt-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat color=grey")
                ui.button("Shame & delete", on_click=confirm).props("color=negative")
        dialog.open()
        # The dialog needs ~300ms to mount before the input is focusable.
        ui.timer(0.3, lambda: name_input.run_method("focus"), once=True)

    def _confirm_clear_queue(self):
        count = len(self.svc.get_queue())
        with ui.dialog() as dialog, ui.card().classes("bg-gray-900 min-w-[300px]"):
            ui.label("Clear queue?").classes("text-lg font-bold")
            ui.label(f"This will remove all {count} songs from the queue.").classes(
                "text-gray-400"
            )

            def clear():
                self.svc.clear_queue()
                self._render_queue()
                self._render_now_playing()
                dialog.close()
                ui.notify("Queue cleared", type="info")

            with ui.row().classes("w-full justify-end gap-2 mt-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat color=grey")
                ui.button("Clear all", on_click=clear).props("color=negative")
        dialog.open()
