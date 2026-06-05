import asyncio
import io
import json
import socket
from dataclasses import dataclass
from datetime import datetime

import segno
from nicegui import ui

from deps import get_service
from keyed_list import KeyedList
from models import (
    PartyEventType,
    filter_queue_with_positions,
    format_clock_eta,
    format_queue_stats,
    search_queue,
)

QUEUE_WINDOW = 30


@dataclass(frozen=True)
class AudienceRowVM:
    uid: str
    track_name: str
    artist: str
    thumb_url: str
    requester: str
    position: int
    eta_ms: int
    is_last: bool
    is_target: bool  # incoming-add animation target (pending_add)
    is_glow: bool  # priority-glow animation target (pending_glow)


PROMINENT_COUNT = 3


def audience_row_vms(
    queue: list,
    *,
    window: int,
    pending_add_uri: str | None,
    pending_glow_uri: str | None,
) -> list[AudienceRowVM]:
    """Pure view-models for the audience queue rows (windowed, with ETA)."""
    positioned = filter_queue_with_positions(queue, "")[:window]
    vms: list[AudienceRowVM] = []
    for i, p in enumerate(positioned):
        item = p.item
        is_target = bool(pending_add_uri) and item.track_uri == pending_add_uri
        is_glow = (
            not is_target
            and bool(pending_glow_uri)
            and item.track_uri == pending_glow_uri
        )
        vms.append(
            AudienceRowVM(
                uid=item.uid,
                track_name=item.track_name,
                artist=item.artist,
                thumb_url=item.thumb_url,
                requester=item.requester or "",
                position=p.position,
                eta_ms=p.eta_ms,
                is_last=i == len(positioned) - 1,
                is_target=is_target,
                is_glow=is_glow,
            )
        )
    return vms


def split_audience_vms(
    vms: list[AudienceRowVM],
) -> tuple[list[AudienceRowVM], list[AudienceRowVM]]:
    """Split windowed row VMs into the prominent head and the scrolling tail.

    The first ``PROMINENT_COUNT`` rows (queue #1-3) render as large cards; the
    rest scroll. ``is_last`` on the VMs is computed against the full window, so
    the scroll tail's own last-row border is handled separately at render time.
    """
    return vms[:PROMINENT_COUNT], vms[PROMINENT_COUNT:]


def _get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def _generate_qr_svg(url: str) -> str:
    qr = segno.make(url)
    buffer = io.BytesIO()
    qr.save(buffer, kind="svg", dark="#4ade80", light=None, border=1, scale=6)
    return buffer.getvalue().decode()


@ui.page("/display", title="VerzoekjesBever", dark=True)
def audience_page():
    svc = get_service()

    ui.add_head_html('<link rel="stylesheet" href="/static/beaver-animation.css">')
    ui.add_head_html('<script src="/static/beaver-animation.js"></script>')
    ui.add_head_html("""
    <style>
        body { background: linear-gradient(135deg, #0d0d1a 0%, #1a1a3e 100%) !important; }
        @media (max-width: 768px) { .qr-overlay { display: none !important; } }
    </style>
    """)

    with ui.column().classes("w-full max-w-3xl mx-auto p-8 gap-6"):
        with ui.column().classes("items-center gap-1"):
            ui.image("/static/beaver.svg").classes("w-12 h-12")
            ui.label("VERZOEKJESBEVER").classes(
                "text-2xl font-extrabold tracking-wide text-white"
            )
            ui.label("REQUEST PARTY").classes("text-xs tracking-[0.3em] text-green-400")

        if not svc.has_session:
            with ui.card().classes("w-full bg-gray-800 rounded-xl p-8 text-center"):
                ui.image("/static/beaver.svg").classes("w-10 h-10 mx-auto")
                ui.label("Waiting for DJ to start the party").classes(
                    "text-xl text-gray-400 mt-2"
                )
                ui.label("Check back soon!").classes("text-gray-500")
            return

        pending_add = {"uri": None}
        pending_glow = {"uri": None}

        # --- now-playing (gated rebuild) ---
        np_container = ui.column().classes("w-full gap-0")
        np_state = {"sig": object()}  # sentinel forces first render

        def render_now_playing():
            current = svc.get_currently_playing()
            sig = (current.uid, current.requester) if current else None
            if sig == np_state["sig"]:
                return
            np_state["sig"] = sig
            np_container.clear()
            with np_container:
                if current:
                    with ui.element("div").classes("now-playing-wrapper w-full"):
                        with ui.card().classes(
                            "w-full bg-green-600 rounded-xl p-5 now-playing-card"
                        ):
                            ui.label("NOW PLAYING").classes(
                                "text-xs tracking-[0.2em] text-white/70"
                            )
                            with ui.row().classes("items-center gap-5 mt-2"):
                                if current.album_art_url:
                                    ui.image(current.album_art_url).classes(
                                        "w-20 h-20 rounded-lg"
                                    )
                                with ui.column().classes("gap-0"):
                                    ui.label(current.track_name).classes(
                                        "text-2xl font-extrabold text-white"
                                    )
                                    ui.label(current.artist).classes(
                                        "text-lg text-white/85"
                                    )
                                    if current.requester:
                                        ui.label(
                                            f"🎤 Requested by {current.requester}"
                                        ).classes("text-sm text-white/60 mt-1")
                else:
                    with ui.card().classes(
                        "w-full bg-gray-800 rounded-xl p-8 text-center"
                    ):
                        ui.image("/static/beaver.svg").classes("w-10 h-10 mx-auto")
                        ui.label("No song playing yet").classes(
                            "text-xl text-gray-400 mt-2"
                        )
                        ui.label("Make a request!").classes("text-gray-500")

        # --- UP NEXT header (patched) ---
        header_row = ui.row().classes("items-center justify-between mt-4 w-full")
        with header_row:
            ui.label("UP NEXT").classes(
                "text-sm font-bold tracking-[0.2em] text-green-400/70"
            )
            stats_label = ui.label("").classes(
                "text-base font-semibold text-green-300/80 "
                "bg-white/5 rounded-full px-4 py-1"
            )

        # --- queue list (KeyedList) ---
        queue_card = ui.card().classes("w-full bg-white/5 rounded-xl p-1")
        with queue_card:
            list_container = ui.column().classes("w-full gap-0")
            more_label = ui.label("").classes("text-center text-gray-500 text-sm py-2")

        # NOTE: leading "nicegui-row" is the framework's default flex class
        # (display:flex; flex-direction:row). _patch_row reapplies BASE_ROW via
        # .classes(replace=...), which wipes ALL classes including the defaults
        # added by ui.row()'s constructor. Without "nicegui-row" here the row
        # collapses to a block and children stack vertically. Any new structural
        # default class must be added to BASE_ROW too, or replace= will nuke it.
        # "beaver-delete-target" gives the row position:relative so the chomp
        # overlay can absolutely-position itself over the row being shame-deleted.
        # Like nicegui-row, it lives in BASE_ROW because _patch_row's
        # .classes(replace=...) wipes anything not re-listed here.
        BASE_ROW = (
            "nicegui-row items-center gap-3 px-4 py-3 w-full beaver-delete-target"
        )
        ETA_NEXT = (
            "text-green-400 font-bold text-sm whitespace-nowrap ml-auto "
            "bg-white/5 rounded-full px-3 py-1 w-28 text-center"
        )
        ETA_WAIT = (
            "text-green-300/70 font-semibold text-sm whitespace-nowrap ml-auto "
            "bg-white/5 rounded-full px-3 py-1 w-28 text-center"
        )

        @dataclass
        class _AudRow:
            root: ui.element  # wrapper div; toggles .queue-add-target
            row: (
                ui.row
            )  # inner row; toggles .beaver-incoming / .priority-glow-target / border
            pos: ui.label
            requester: ui.label
            eta: ui.label
            eta_cls: str = ""
            row_cls: str = ""
            root_cls: str = ""

        def _patch_row(h: _AudRow, vm: AudienceRowVM) -> None:
            if h.pos.text != str(vm.position):
                h.pos.set_text(str(vm.position))
            req_text = f"🎤 {vm.requester}" if vm.requester else ""
            if h.requester.text != req_text:
                h.requester.set_text(req_text)
            h.requester.set_visibility(bool(vm.requester))
            if vm.eta_ms == 0:
                eta_text, eta_cls = "Up next", ETA_NEXT
            else:
                clock = format_clock_eta(
                    svc.get_current_remaining_ms() + vm.eta_ms, datetime.now()
                )
                eta_text, eta_cls = f"ETA {clock}", ETA_WAIT
            if h.eta.text != eta_text:
                h.eta.set_text(eta_text)
            if h.eta_cls != eta_cls:
                h.eta.classes(replace=eta_cls)
                h.eta_cls = eta_cls
            row_cls = BASE_ROW + ("" if vm.is_last else " border-b border-white/5")
            if vm.is_target:
                row_cls += " beaver-incoming"
            if vm.is_glow:
                row_cls += " priority-glow-target"
            if h.row_cls != row_cls:
                h.row.classes(replace=row_cls)
                h.row_cls = row_cls
            root_cls = "w-full queue-add-target" if vm.is_target else "w-full"
            if h.root_cls != root_cls:
                h.root.classes(replace=root_cls)
                h.root_cls = root_cls

        def _build_row(vm: AudienceRowVM) -> _AudRow:
            wrapper = ui.element("div").classes("w-full")
            with wrapper:
                row = ui.row().classes(BASE_ROW)
                row.props(f'data-uid="{vm.uid}"')
                with row:
                    pos = ui.label(str(vm.position)).classes(
                        "text-green-400 font-extrabold text-lg w-7 text-center"
                    )
                    if vm.thumb_url:
                        ui.image(vm.thumb_url).classes("w-11 h-11 rounded-md")
                    with ui.column().classes("flex-grow gap-0"):
                        ui.label(vm.track_name).classes(
                            "text-white font-semibold text-base"
                        )
                        ui.label(vm.artist).classes("text-gray-400 text-sm")
                        requester = ui.label("").classes(
                            "text-orange-400 text-xs mt-0.5"
                        )
                    eta = ui.label("").classes(ETA_WAIT)
            handle = _AudRow(
                root=wrapper, row=row, pos=pos, requester=requester, eta=eta
            )
            _patch_row(handle, vm)
            return handle

        queue_list = KeyedList(
            list_container,
            key=lambda vm: vm.uid,
            build=_build_row,
            patch=_patch_row,
        )

        def render_queue():
            queue = svc.get_queue()
            stats_label.set_text(
                format_queue_stats(
                    queue, svc.get_current_remaining_ms(), datetime.now()
                )
                if queue
                else ""
            )
            header_row.set_visibility(bool(queue))
            queue_card.set_visibility(bool(queue))
            vms = audience_row_vms(
                queue,
                window=QUEUE_WINDOW,
                pending_add_uri=pending_add["uri"],
                pending_glow_uri=pending_glow["uri"],
            )
            queue_list.reconcile(vms)
            hidden = len(queue) - len(vms)
            more_label.set_visibility(hidden > 0)
            if hidden > 0:
                more_label.set_text(f"+ {hidden} more song{'s' if hidden != 1 else ''}")

        def render_all():
            render_now_playing()
            render_queue()

        render_all()

        display_url = f"http://{_get_local_ip()}:8000/display"
        qr_svg = _generate_qr_svg(display_url)

        @ui.refreshable
        def qr_overlay():
            if svc.show_qr_code:
                with (
                    ui.element("div")
                    .classes("qr-overlay")
                    .style(
                        "position: fixed; bottom: 24px; left: 24px; z-index: 100; "
                        "background: rgba(255,255,255,0.06); backdrop-filter: blur(8px); "
                        "border-radius: 16px; padding: 16px; text-align: center; "
                        "display: flex; flex-direction: column; align-items: center;"
                    )
                ):
                    ui.html(qr_svg)
                    ui.label("Scan to follow along!").classes(
                        "text-sm font-semibold text-green-400 mt-2"
                    )

        qr_overlay()

        with (
            ui.dialog() as search_dialog,
            ui.card().classes("w-full max-w-md bg-gray-900 rounded-xl p-5 gap-3"),
        ):
            ui.label("🔍 Find your song").classes("text-lg font-bold text-white")
            search_input = (
                ui.input("Song, artist, or your name")
                .classes("w-full")
                .props("autofocus clearable dark")
            )

            @ui.refreshable
            def search_results():
                query = (search_input.value or "").strip()
                if not query:
                    ui.label("Type a song, artist, or your name").classes(
                        "text-gray-500 text-sm"
                    )
                    return
                matches = search_queue(
                    svc.get_queue(), svc.get_currently_playing(), query
                )
                if not matches:
                    ui.label("Not in the queue right now").classes("text-gray-400")
                    ui.label("Ask the DJ!").classes("text-gray-500 text-sm")
                    return
                for match in matches:
                    with ui.row().classes(
                        "items-center gap-3 w-full py-2 border-b border-white/5"
                    ):
                        with ui.column().classes("gap-0 flex-grow"):
                            ui.label(match.item.track_name).classes(
                                "text-white font-semibold"
                            )
                            ui.label(match.item.artist).classes("text-gray-400 text-sm")
                        if match.now_playing:
                            ui.label("🎉 Playing right now!").classes(
                                "text-green-400 font-bold whitespace-nowrap"
                            )
                        elif match.eta_ms == 0:
                            ui.label(f"#{match.position} · Up next!").classes(
                                "text-green-300 font-semibold whitespace-nowrap"
                            )
                        else:
                            eta = format_clock_eta(
                                svc.get_current_remaining_ms() + match.eta_ms,
                                datetime.now(),
                            )
                            ui.label(f"#{match.position} · ETA {eta}").classes(
                                "text-green-300 font-semibold whitespace-nowrap"
                            )

            search_input.on_value_change(lambda: search_results.refresh())
            search_results()
            ui.button("Close", on_click=search_dialog.close).props("flat").classes(
                "self-end text-gray-400"
            )

        ui.button(icon="search", on_click=search_dialog.open).props(
            "round color=green"
        ).style(
            "position: fixed; bottom: 24px; right: 24px; z-index: 100; opacity: 0.55;"
        )

        with (
            ui.dialog() as info_dialog,
            ui.card().classes("w-full max-w-md bg-gray-900 rounded-xl p-5 gap-2"),
        ):
            ui.label("🦫 How this works").classes("text-lg font-bold text-white")
            ui.label(
                "This screen shows what's playing now and what's coming up next."
            ).classes("text-gray-300 text-sm")
            ui.label("Only the DJ adds songs. Go ask them for your request!").classes(
                "text-gray-300 text-sm"
            )
            ui.label(
                f"The list shows the next {QUEUE_WINDOW} songs. "
                "If there are more, you'll see a '+ N more songs' line."
            ).classes("text-gray-300 text-sm")
            ui.label(
                "Tap 🔍 to find your song and see its position and how long "
                "until it plays."
            ).classes("text-gray-300 text-sm")
            ui.button("Got it", on_click=info_dialog.close).props("flat").classes(
                "self-end text-gray-400"
            )

        ui.button(icon="info", on_click=info_dialog.open).props(
            "round color=grey"
        ).style(
            "position: fixed; bottom: 84px; right: 24px; z-index: 100; opacity: 0.45;"
        )

        local_version = {"v": svc.version}

        async def check_updates():
            if svc.version == local_version["v"]:
                return
            events = svc.get_events_since(local_version["v"])
            local_version["v"] = svc.version

            for event in events:
                if event.kind == PartyEventType.SKIPPED and svc.beaver_enabled:
                    await ui.run_javascript("triggerBeaverAnimation()")
                    await asyncio.sleep(2.2)

                if event.kind == PartyEventType.SHAME_DELETE:
                    if svc.beaver_enabled and event.uid:
                        await ui.run_javascript(
                            f"triggerBeaverDeleteAnimation({json.dumps(event.uid)})"
                        )
                        await asyncio.sleep(2.2)
                    if event.message:
                        await ui.run_javascript(
                            f"triggerShameOverlay({json.dumps(event.message)})"
                        )
                        await asyncio.sleep(6)

                if event.kind == PartyEventType.ADDED and svc.beaver_enabled:
                    pending_add["uri"] = event.track_uri
                if event.kind == PartyEventType.MOVED_TO_TOP:
                    pending_glow["uri"] = event.track_uri
                elif (
                    event.kind == PartyEventType.ADDED
                    and event.is_priority
                    and not svc.beaver_enabled
                ):
                    pending_glow["uri"] = event.track_uri

            render_all()
            qr_overlay.refresh()
            if (search_input.value or "").strip():
                search_results.refresh()

            if pending_add["uri"]:
                is_priority = any(
                    e.kind == PartyEventType.ADDED and e.is_priority for e in events
                )
                await ui.run_javascript(
                    f"triggerBeaverAddAnimation({str(is_priority).lower()})"
                )
                await asyncio.sleep(3.5 if is_priority else 2.4)
                pending_add["uri"] = None
                render_queue()  # clear the incoming class now the animation is done

            if pending_glow["uri"]:
                await ui.run_javascript("triggerPriorityGlow()")
                await asyncio.sleep(2.0)
                pending_glow["uri"] = None
                render_queue()

        ui.timer(1.0, check_updates)
