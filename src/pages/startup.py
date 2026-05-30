from nicegui import app, ui

from config import CONFIG
from deps import get_service


@ui.page("/", title="VerzoekjesBever - Setup", dark=True)
def setup_page():
    if CONFIG.dj_password.get_secret_value() and not app.storage.user.get(
        "authenticated"
    ):
        ui.navigate.to("/login")
        return
    svc = get_service()

    with ui.column().classes("w-full max-w-lg mx-auto mt-16 gap-6"):
        ui.label("🦫").classes("text-6xl text-center w-full")
        ui.label("VerzoekjesBever").classes("text-3xl font-bold text-center w-full")
        ui.label("Setup your party").classes("text-gray-400 text-center w-full")

        ui.separator()

        if svc.has_session:
            with ui.card().classes("w-full bg-green-900/30 border border-green-700"):
                ui.label("Previous session found").classes(
                    "text-lg font-semibold text-green-400"
                )
                ui.label(f"Session: {svc.session_name}").classes("text-gray-400")
                ui.label(f"Queue: {len(svc.get_queue())} songs").classes(
                    "text-gray-400"
                )
                ui.button(
                    "Resume Session",
                    on_click=lambda: ui.navigate.to("/dj"),
                ).props("color=positive").classes("w-full mt-2")

            ui.separator()

        ui.label("New Session").classes("text-lg font-semibold")
        session_name = ui.input(
            "Session name", value="VerzoekjesBever - Party"
        ).classes("w-full")

        ui.label("Select playback device").classes("text-sm text-gray-400 mt-2")
        devices = svc.get_devices()
        device_options = {d["id"]: f"{d['name']} ({d['type']})" for d in devices}

        if not device_options:
            ui.label(
                "No Spotify devices found. Open Spotify on a device first."
            ).classes("text-orange-400 italic")

        device_select = ui.select(
            options=device_options,
            label="Device",
            value=next(iter(device_options), None),
        ).classes("w-full")

        def refresh_devices():
            new_devices = svc.get_devices()
            new_options = {d["id"]: f"{d['name']} ({d['type']})" for d in new_devices}
            device_select.options = new_options
            device_select.update()
            if new_options and device_select.value is None:
                device_select.value = next(iter(new_options))
            ui.notify(f"Found {len(new_options)} device(s)", type="info")

        ui.button("Refresh devices", on_click=refresh_devices).props("flat color=grey")

        demo_toggle = ui.checkbox("Pre-fill queue with 50 demo songs").classes("w-full")

        def start_new():
            if not device_select.value:
                ui.notify("Select a device first", type="warning")
                return
            svc.start_session(
                session_name.value, device_select.value, demo=demo_toggle.value
            )
            ui.navigate.to("/dj")

        ui.button("Start Session", on_click=start_new).props("color=positive").classes(
            "w-full"
        )
