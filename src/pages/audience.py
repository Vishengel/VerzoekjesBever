import asyncio
import contextlib
import io
import socket

import segno
from nicegui import ui

from deps import get_service
from models import PartyEventType, format_queue_duration, search_queue

QUEUE_WINDOW = 30


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

        @ui.refreshable
        def playlist_display():
            current = svc.get_currently_playing()

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
                with ui.card().classes("w-full bg-gray-800 rounded-xl p-8 text-center"):
                    ui.image("/static/beaver.svg").classes("w-10 h-10 mx-auto")
                    ui.label("No song playing yet").classes(
                        "text-xl text-gray-400 mt-2"
                    )
                    ui.label("Make a request!").classes("text-gray-500")

            queue = svc.get_queue()
            if queue:
                with ui.row().classes("items-center justify-between mt-4 w-full"):
                    ui.label("UP NEXT").classes(
                        "text-sm font-bold tracking-[0.2em] text-green-400/70"
                    )
                    total_ms = sum(item.duration_ms for item in queue)
                    stats = f"⏱ {len(queue)} songs"
                    if total_ms:
                        stats += f" · {format_queue_duration(total_ms)} remaining"
                    ui.label(stats).classes(
                        "text-base font-semibold text-green-300/80 "
                        "bg-white/5 rounded-full px-4 py-1"
                    )
                with ui.card().classes("w-full bg-white/5 rounded-xl p-1"):
                    visible = queue[:QUEUE_WINDOW]
                    for i, item in enumerate(visible):
                        border = (
                            "border-b border-white/5" if i < len(visible) - 1 else ""
                        )
                        is_target = (
                            pending_add["uri"] and item.track_uri == pending_add["uri"]
                        )
                        is_glow = (
                            not is_target
                            and pending_glow["uri"]
                            and item.track_uri == pending_glow["uri"]
                        )

                        container = (
                            ui.element("div").classes("queue-add-target")
                            if is_target
                            else contextlib.nullcontext()
                        )

                        with container:
                            row_classes = f"items-center gap-3 px-4 py-3 {border}"
                            if is_target:
                                row_classes += " beaver-incoming"
                            if is_glow:
                                row_classes += " priority-glow-target"
                            with ui.row().classes(row_classes):
                                ui.label(str(i + 1)).classes(
                                    "text-green-400 font-extrabold text-lg w-7 text-center"
                                )
                                if item.album_art_url:
                                    ui.image(item.album_art_url).classes(
                                        "w-11 h-11 rounded-md"
                                    )
                                with ui.column().classes("flex-grow gap-0"):
                                    ui.label(item.track_name).classes(
                                        "text-white font-semibold text-base"
                                    )
                                    ui.label(item.artist).classes(
                                        "text-gray-400 text-sm"
                                    )
                                    if item.requester:
                                        ui.label(f"🎤 {item.requester}").classes(
                                            "text-orange-400 text-xs mt-0.5"
                                        )
                    hidden = len(queue) - len(visible)
                    if hidden > 0:
                        ui.label(
                            f"+ {hidden} more song{'s' if hidden != 1 else ''}"
                        ).classes("text-center text-gray-500 text-sm py-2")

        playlist_display()

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
                            eta = format_queue_duration(match.eta_ms)
                            ui.label(f"#{match.position} · ~{eta}").classes(
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
            ui.label("Only the DJ adds songs — go ask them for your request!").classes(
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

            playlist_display.refresh()
            qr_overlay.refresh()
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

            if pending_glow["uri"]:
                await ui.run_javascript("triggerPriorityGlow()")
                await asyncio.sleep(2.0)
                pending_glow["uri"] = None

        ui.timer(1.0, check_updates)
