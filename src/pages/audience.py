import asyncio
import io
import json
import socket
from dataclasses import dataclass
from datetime import datetime

import segno
from nicegui import ui

from config import CONFIG
from deps import get_service
from keyed_list import KeyedList
from models import (
    PartyEventType,
    filter_queue_with_positions,
    format_clock_eta,
    format_queue_stats,
    search_queue,
)


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


PROMINENT_COUNT = 1


def audience_row_vms(queue: list, *, window: int) -> list[AudienceRowVM]:
    """Pure view-models for the audience queue rows (windowed, with ETA).

    Beaver animations are zone-based (now-playing card, prominent up-next card,
    or the scroll box) rather than row-targeted, so rows carry no animation
    flags — the JS targets stable, always-visible zones instead.
    """
    positioned = filter_queue_with_positions(queue, "")[:window]
    vms: list[AudienceRowVM] = []
    for i, p in enumerate(positioned):
        item = p.item
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
            )
        )
    return vms


def split_audience_vms(
    vms: list[AudienceRowVM],
) -> tuple[list[AudienceRowVM], list[AudienceRowVM]]:
    """Split windowed row VMs into the prominent head and the scrolling tail.

    The first ``PROMINENT_COUNT`` rows render as large cards; the rest scroll.
    ``is_last`` on the VMs is computed against the full window, so the scroll
    tail's own last-row border is handled separately at render time.
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
    ui.add_head_html('<link rel="stylesheet" href="/static/audience-scroll.css">')
    ui.add_head_html('<script src="/static/audience-scroll.js"></script>')
    ui.add_head_html("""
    <style>
        body { background: linear-gradient(135deg, #0d0d1a 0%, #1a1a3e 100%) !important; }
        @media (max-width: 768px) { .qr-overlay { display: none !important; } }
    </style>
    """)

    # h-screen + overflow-hidden makes the billboard fill exactly the viewport;
    # the scroll region flex-grows into the leftover space (below), so the page
    # never scrolls and the COMING UP box — and its beaver — stay on screen.
    with ui.column().classes(
        "w-full max-w-3xl mx-auto p-8 gap-6 h-screen overflow-hidden"
    ):
        # Compact horizontal brand bar (logo + title inline) frees vertical room
        # for the queue. Stays a slim strip on mobile — a true sidebar would be
        # too cramped on narrow phones.
        with ui.row().classes("items-center gap-3 w-full"):
            ui.image("/static/beaver.svg").classes("w-10 h-10")
            with ui.column().classes("gap-0"):
                ui.label("VERZOEKJESBEVER").classes(
                    "text-xl font-extrabold tracking-wide text-white leading-tight"
                )
                ui.label("REQUEST PARTY").classes(
                    "text-[0.6rem] tracking-[0.3em] text-green-400"
                )

        if not svc.has_session:
            with ui.card().classes("w-full bg-gray-800 rounded-xl p-8 text-center"):
                ui.image("/static/beaver.svg").classes("w-10 h-10 mx-auto")
                ui.label("Waiting for DJ to start the party").classes(
                    "text-xl text-gray-400 mt-2"
                )
                ui.label("Check back soon!").classes("text-gray-500")
            return

        # --- now-playing (built once, patched in place) ---
        # Both the playing card and the empty card are built up front and
        # toggled by visibility. Patching labels/image in place (gated by song
        # uid) avoids the clear+rebuild flash where the card briefly vanished.
        np_state = {"sig": object()}  # sentinel forces first render
        with ui.column().classes("w-full gap-0"):
            np_wrapper = ui.element("div").classes("now-playing-wrapper w-full")
            with np_wrapper:
                with ui.card().classes(
                    "w-full bg-green-600 rounded-xl p-5 now-playing-card"
                ):
                    ui.label("NOW PLAYING").classes(
                        "text-xs tracking-[0.2em] text-white/70"
                    )
                    with ui.row().classes("items-center gap-5 mt-2"):
                        np_img = ui.image("").classes("w-20 h-20 rounded-lg")
                        with ui.column().classes("gap-0"):
                            np_track = ui.label("").classes(
                                "text-2xl font-extrabold text-white"
                            )
                            np_artist = ui.label("").classes("text-lg text-white/85")
                            np_req = ui.label("").classes("text-sm text-white/60 mt-1")
            np_empty = ui.card().classes(
                "w-full bg-gray-800 rounded-xl p-8 text-center"
            )
            with np_empty:
                ui.image("/static/beaver.svg").classes("w-10 h-10 mx-auto")
                ui.label("No song playing yet").classes("text-xl text-gray-400 mt-2")
                ui.label("Make a request!").classes("text-gray-500")

        def render_now_playing():
            current = svc.get_currently_playing()
            sig = (current.uid, current.requester) if current else None
            if sig == np_state["sig"]:
                return
            np_state["sig"] = sig
            if current:
                np_img.set_source(current.album_art_url or "")
                np_img.set_visibility(bool(current.album_art_url))
                np_track.set_text(current.track_name)
                np_artist.set_text(current.artist)
                np_req.set_text(
                    f"🎤 Requested by {current.requester}" if current.requester else ""
                )
                np_req.set_visibility(bool(current.requester))
            np_wrapper.set_visibility(bool(current))
            np_empty.set_visibility(not current)

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

        # --- prominent cards (queue #1-3) ---
        # "prominent-cards" lets the delete-beaver JS scope its data-uid lookup
        # to these always-visible cards.
        prominent_container = ui.column().classes("prominent-cards w-full gap-2")

        # --- COMING UP scroll region ---
        coming_up_header = ui.label("COMING UP").classes(
            "text-xs font-bold tracking-[0.2em] text-green-400/50 mt-3"
        )

        def _loop_marker() -> None:
            # Beaver divider that scrolls past once per loop, punctuating the
            # seam where the last song wraps back to the top. Lives at the end
            # of BOTH halves (real + clone) so the -50% wrap stays seamless;
            # CSS hides it when the queue isn't scrolling.
            with ui.row().classes(
                "loop-marker items-center justify-center py-5 w-full"
            ):
                ui.image("/static/beaver.svg").classes("w-8 h-8")

        scroll_region = ui.element("div").classes(
            "scroll-region w-full flex-grow min-h-0"
        )
        with scroll_region:
            scroll_track = ui.element("div").classes("scroll-track w-full")
            with scroll_track:
                # Two equal halves: the live rows + a duplicate, each capped by a
                # loop marker. The JS scrolls scroll-top by pixels and wraps after
                # one half (.scroll-real height), so the clone makes the loop
                # seamless. Both halves are KeyedLists patched in place — no
                # clear/rebuild flash, and pixel scrolling is insert-stable.
                real_wrap = ui.element("div").classes("scroll-real w-full")
                with real_wrap:
                    list_container = ui.column().classes("w-full gap-0")
                    _loop_marker()
                clone_wrap = ui.element("div").classes("scroll-clone w-full")
                with clone_wrap:
                    clone_container = ui.column().classes("w-full gap-0")
                    _loop_marker()
        more_label = ui.label("").classes("text-center text-gray-500 text-sm py-2")

        # NOTE: leading "nicegui-row" is the framework's default flex class
        # (display:flex; flex-direction:row). _patch_row reapplies BASE_ROW via
        # .classes(replace=...), which wipes ALL classes including the defaults
        # added by ui.row()'s constructor. Without "nicegui-row" here the row
        # collapses to a block and children stack vertically. Any new structural
        # default class must be added to BASE_ROW too, or replace= will nuke it.
        BASE_ROW = "nicegui-row items-center gap-3 px-4 py-3 w-full"
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
            root: ui.row  # the row element (KeyedList moves/deletes this)
            pos: ui.label
            requester: ui.label
            eta: ui.label
            eta_cls: str = ""
            row_cls: str = ""

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
            if h.row_cls != row_cls:
                h.row_cls = row_cls
                h.root.classes(replace=row_cls)

        def _build_row(vm: AudienceRowVM) -> _AudRow:
            row = ui.row().classes(BASE_ROW)
            with row:
                pos = ui.label(str(vm.position)).classes(
                    "text-green-400 font-extrabold text-lg w-7 text-center"
                )
                if vm.thumb_url:
                    ui.image(vm.thumb_url).classes("w-11 h-11 rounded-md").props(
                        "loading=lazy"
                    )
                with ui.column().classes("flex-grow gap-0"):
                    ui.label(vm.track_name).classes(
                        "text-white font-semibold text-base"
                    )
                    ui.label(vm.artist).classes("text-gray-400 text-sm")
                    requester = ui.label("").classes("text-orange-400 text-xs mt-0.5")
                eta = ui.label("").classes(ETA_WAIT)
            handle = _AudRow(root=row, pos=pos, requester=requester, eta=eta)
            _patch_row(handle, vm)
            return handle

        queue_list = KeyedList(
            list_container,
            key=lambda vm: vm.uid,
            build=_build_row,
            patch=_patch_row,
        )
        # Clone half: same rows, same builder/patcher, its own container. Patched
        # in place each render (no clear/rebuild flash) so the seamless-loop seam
        # always matches the live half.
        clone_list = KeyedList(
            clone_container,
            key=lambda vm: vm.uid,
            build=_build_row,
            patch=_patch_row,
        )

        @dataclass
        class _PromRow:
            root: ui.element
            pos: ui.label
            track_name: ui.label
            artist: ui.label
            requester: ui.label
            eta: ui.label
            eta_text: str = ""
            eta_cls: str = ""

        def _patch_prom(h: _PromRow, vm: AudienceRowVM) -> None:
            if h.pos.text != str(vm.position):
                h.pos.set_text(str(vm.position))
            if h.track_name.text != vm.track_name:
                h.track_name.set_text(vm.track_name)
            if h.artist.text != vm.artist:
                h.artist.set_text(vm.artist)
            req_text = f"🎤 {vm.requester}" if vm.requester else ""
            if h.requester.text != req_text:
                h.requester.set_text(req_text)
            h.requester.set_visibility(bool(vm.requester))
            if vm.eta_ms == 0:
                eta_text, eta_cls = "Up next", ETA_NEXT
            else:
                eta_text = "ETA " + format_clock_eta(
                    svc.get_current_remaining_ms() + vm.eta_ms, datetime.now()
                )
                eta_cls = ETA_WAIT
            if h.eta_text != eta_text:
                h.eta.set_text(eta_text)
                h.eta_text = eta_text
            if h.eta_cls != eta_cls:
                h.eta.classes(replace=eta_cls)
                h.eta_cls = eta_cls

        def _build_prom(vm: AudienceRowVM) -> _PromRow:
            card = ui.card().classes(
                "w-full bg-white/10 rounded-xl p-4 nicegui-row "
                "items-center gap-4 flex-row beaver-delete-target"
            )
            # data-uid + beaver-delete-target: the delete-beaver chomps THIS card
            # when the removed song is one of the prominent up-next cards.
            card.props(f'data-uid="{vm.uid}"')
            with card:
                pos = ui.label(str(vm.position)).classes(
                    "text-green-400 font-extrabold text-2xl w-8 text-center"
                )
                if vm.thumb_url:
                    ui.image(vm.thumb_url).classes("w-16 h-16 rounded-lg").props(
                        "loading=lazy"
                    )
                with ui.column().classes("flex-grow gap-0"):
                    track_name = ui.label(vm.track_name).classes(
                        "text-white font-bold text-xl"
                    )
                    artist = ui.label(vm.artist).classes("text-gray-300 text-base")
                    requester = ui.label("").classes("text-orange-400 text-sm mt-0.5")
                eta = ui.label("").classes(ETA_NEXT)
            handle = _PromRow(
                root=card,
                pos=pos,
                track_name=track_name,
                artist=artist,
                requester=requester,
                eta=eta,
            )
            _patch_prom(handle, vm)
            return handle

        prominent_list = KeyedList(
            prominent_container,
            key=lambda vm: vm.uid,
            build=_build_prom,
            patch=_patch_prom,
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
            vms = audience_row_vms(queue, window=CONFIG.audience_queue_window)
            prominent_vms, scroll_vms = split_audience_vms(vms)
            prominent_list.reconcile(prominent_vms)
            queue_list.reconcile(scroll_vms)
            clone_list.reconcile(scroll_vms)

            has_scroll = bool(scroll_vms)
            coming_up_header.set_visibility(has_scroll)
            scroll_region.set_visibility(has_scroll)
            prominent_container.set_visibility(bool(prominent_vms))

            hidden = len(queue) - len(vms)
            more_label.set_visibility(hidden > 0)
            if hidden > 0:
                more_label.set_text(f"+ {hidden} more song{'s' if hidden != 1 else ''}")

        def render_all():
            render_now_playing()
            render_queue()

        render_all()

        async def _init_scroll():
            await ui.run_javascript("setupAudienceScroll(); updateAudienceScroll()")

        ui.timer(0.2, _init_scroll, once=True)

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
                f"The list shows the next {CONFIG.audience_queue_window} songs. "
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

            # Zone-based beaver dispatch: each event animates a stable, visible
            # zone (now-playing card / prominent up-next card / scroll box),
            # never a row that may be scrolled off-screen or duplicated.
            top_beaver = False  # priority add (beaver on) -> reveal prominent card
            box_beaver = False  # regular add (beaver on) -> toss onto scroll box
            glow = False  # move-to-top, or priority add (beaver off) -> card glow
            for event in events:
                if event.kind == PartyEventType.SKIPPED and svc.beaver_enabled:
                    await ui.run_javascript("triggerBeaverAnimation()")
                    # Chomp keyframes run 2.0s; runBeaverDestroy clears its class
                    # at 2.2s. Rebuild the now-playing card at 2.0s — right as the
                    # chomp finishes — so the new song swaps in before the card
                    # snaps back, instead of racing the cleanup (caused a flicker).
                    await asyncio.sleep(2.0)

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

                if event.kind == PartyEventType.ADDED:
                    if event.is_priority:
                        top_beaver = top_beaver or svc.beaver_enabled
                        glow = glow or not svc.beaver_enabled
                    elif svc.beaver_enabled:
                        box_beaver = True
                if event.kind == PartyEventType.MOVED_TO_TOP:
                    glow = True

            render_all()
            qr_overlay.refresh()
            await ui.run_javascript("updateAudienceScroll()")
            if (search_input.value or "").strip():
                search_results.refresh()

            if top_beaver:
                await ui.run_javascript("triggerBeaverPromote()")
                await asyncio.sleep(3.5)
            if box_beaver:
                await ui.run_javascript("triggerBeaverBoxAdd()")
                await asyncio.sleep(2.4)
            if glow:
                await ui.run_javascript("triggerPromoteGlow()")
                await asyncio.sleep(2.0)

        ui.timer(1.0, check_updates)
