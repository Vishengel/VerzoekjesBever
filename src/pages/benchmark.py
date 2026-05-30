import time

from nicegui import app, ui

from config import CONFIG
from deps import get_service
from load_test_utils import make_fake_items

SIZES = [10, 50, 100, 500]


@ui.page("/benchmark", title="VerzoekjesBever - Benchmark", dark=True)
def benchmark_page():
    if CONFIG.dj_password.get_secret_value() and not app.storage.user.get(
        "authenticated"
    ):
        ui.navigate.to("/login")
        return
    svc = get_service()

    with ui.column().classes("w-full max-w-lg mx-auto mt-16 gap-6"):
        ui.label("Queue Load Benchmark").classes(
            "text-3xl font-bold text-center w-full"
        )
        ui.label("Developer tool for testing queue performance at scale").classes(
            "text-gray-400 text-center w-full"
        )

        ui.separator()

        size_select = ui.select(
            options={s: f"{s} items" for s in SIZES},
            value=SIZES[0],
            label="Queue size",
        ).classes("w-full")

        timing_label = ui.label("").classes("text-center w-full")

        def fill_queue():
            if not svc.has_session:
                ui.notify("Start a session first (go to /)", type="warning")
                return
            items = make_fake_items(size_select.value)
            start = time.perf_counter()
            svc.fill_benchmark_queue(items)
            elapsed = (time.perf_counter() - start) * 1000
            timing_label.text = f"Filled {size_select.value} items in {elapsed:.0f}ms"
            ui.notify(f"Queue filled with {size_select.value} items", type="positive")

        def clear_queue():
            svc.clear_queue()
            timing_label.text = ""
            ui.notify("Queue cleared", type="info")

        with ui.row().classes("w-full gap-4"):
            ui.button("Fill queue", on_click=fill_queue).props(
                "color=positive"
            ).classes("flex-1")
            ui.button("Clear queue", on_click=clear_queue).props(
                "color=negative"
            ).classes("flex-1")

        ui.separator()

        ui.label("Inspect rendering").classes("text-lg font-semibold")
        ui.label(
            "After filling the queue, open these pages to check rendering performance:"
        ).classes("text-gray-400")

        with ui.row().classes("w-full gap-4"):
            ui.link("DJ Page", "/dj", new_tab=True).classes("text-blue-400 underline")
            ui.link("Audience Page", "/display", new_tab=True).classes(
                "text-blue-400 underline"
            )

        ui.separator()

        ui.label(f"Current queue size: {len(svc.get_queue())}").classes(
            "text-gray-400 text-center w-full"
        )
