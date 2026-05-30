import asyncio
import contextlib
import io
import socket

import segno
from nicegui import ui

from deps import get_service


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except OSError:
        ip = "127.0.0.1"
    return ip


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
            ui.label("🦫").classes("text-5xl")
            ui.label("VERZOEKJESBEVER").classes(
                "text-2xl font-extrabold tracking-wide text-white"
            )
            ui.label("REQUEST PARTY").classes("text-xs tracking-[0.3em] text-green-400")

        if not svc.has_session:
            with ui.card().classes("w-full bg-gray-800 rounded-xl p-8 text-center"):
                ui.label("🦫").classes("text-4xl")
                ui.label("Waiting for DJ to start the party").classes(
                    "text-xl text-gray-400 mt-2"
                )
                ui.label("Check back soon!").classes("text-gray-500")
            return

        pending_add = {"uri": None, "top": False}

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
                    ui.label("🦫").classes("text-4xl")
                    ui.label("No song playing yet").classes(
                        "text-xl text-gray-400 mt-2"
                    )
                    ui.label("Make a request!").classes("text-gray-500")

            queue = svc.get_queue()
            if queue:
                ui.label("UP NEXT").classes(
                    "text-sm font-bold tracking-[0.2em] text-green-400/70 mt-4"
                )
                with ui.card().classes("w-full bg-white/5 rounded-xl p-1"):
                    for i, item in enumerate(queue):
                        border = "border-b border-white/5" if i < len(queue) - 1 else ""
                        is_target = (
                            pending_add["uri"] and item.track_uri == pending_add["uri"]
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

        local_version = {"v": svc.version}
        local_skip_version = {"v": svc.last_skip_version}
        local_add_version = {"v": svc.last_add_version}

        async def check_updates():
            if svc.version != local_version["v"]:
                skip_happened = (
                    svc.beaver_enabled
                    and svc.last_skip_version > local_skip_version["v"]
                )
                add_happened = (
                    svc.beaver_enabled and svc.last_add_version > local_add_version["v"]
                )

                local_version["v"] = svc.version
                local_skip_version["v"] = svc.last_skip_version
                local_add_version["v"] = svc.last_add_version

                if skip_happened:
                    await ui.run_javascript("triggerBeaverAnimation()")
                    await asyncio.sleep(2.2)

                if add_happened:
                    pending_add["uri"] = svc.last_added_uri
                    pending_add["top"] = svc.last_add_was_top

                playlist_display.refresh()
                qr_overlay.refresh()

                if add_happened:
                    is_priority = pending_add["top"]
                    await ui.run_javascript(
                        f"triggerBeaverAddAnimation({str(is_priority).lower()})"
                    )
                    await asyncio.sleep(3.5 if is_priority else 2.4)
                    pending_add["uri"] = None

        ui.timer(1.0, check_updates)
