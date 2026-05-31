import hmac

from nicegui import app, ui

from config import CONFIG


@ui.page("/login", title="VerzoekjesBever - Login", dark=True)
def login_page():
    if not CONFIG.dj_password.get_secret_value():
        ui.navigate.to("/")
        return

    if app.storage.user.get("authenticated"):
        ui.navigate.to("/")
        return

    def try_login():
        if hmac.compare_digest(
            password_input.value, CONFIG.dj_password.get_secret_value()
        ):
            app.storage.user["authenticated"] = True
            ui.navigate.to("/")
        else:
            ui.notify("Wrong password", type="negative")

    with ui.column().classes("w-full max-w-sm mx-auto mt-32 gap-6 items-center"):
        ui.image("/static/beaver.svg").classes("w-16 h-16")
        ui.label("VerzoekjesBever").classes("text-3xl font-bold")
        ui.label("Enter DJ password").classes("text-gray-400")

        password_input = (
            ui.input("Password", password=True, password_toggle_button=True)
            .classes("w-full")
            .on("keydown.enter", try_login)
        )

        ui.button("Login", on_click=try_login).props("color=positive").classes("w-full")
