import asyncio

from nicegui import ui

from main import get_service


@ui.page("/display", title="VerzoekjesBever", dark=True)
def audience_page():
    svc = get_service()

    ui.add_head_html("""
    <style>
        body { background: linear-gradient(135deg, #0d0d1a 0%, #1a1a3e 100%) !important; }

        .now-playing-wrapper {
            position: relative;
            overflow: visible;
        }

        .beaver-overlay {
            position: absolute;
            inset: 0;
            pointer-events: none;
            z-index: 50;
            overflow: hidden;
        }

        .beaver-actor {
            position: absolute;
            font-size: 80px;
            line-height: 1;
            filter: drop-shadow(0 0 10px rgba(0,0,0,0.5));
        }

        /* Chomp animation */
        @keyframes chomp-slide-in {
            0% { transform: translateX(-150%) rotate(-10deg); }
            30% { transform: translateX(10%) rotate(5deg); }
            50% { transform: translateX(30%) rotate(-5deg) scaleX(-1); }
            70% { transform: translateX(50%) rotate(5deg); }
            100% { transform: translateX(150%) rotate(10deg); }
        }

        @keyframes chomp-card-shake {
            0%, 100% { transform: translateX(0); opacity: 1; }
            20% { transform: translateX(-8px) rotate(-1deg); }
            30% { transform: translateX(8px) rotate(1deg); opacity: 0.7; }
            40% { transform: translateX(-5px); }
            50% { transform: translateX(5px); opacity: 0.5; }
            60% { transform: translateX(-3px); opacity: 0.6; }
            80% { transform: translateX(0); opacity: 0.8; }
        }

        .beaver-chomp .beaver-actor {
            top: 50%;
            left: 0;
            margin-top: -40px;
            animation: chomp-slide-in 2s ease-in-out forwards;
        }

        .beaver-chomp .now-playing-card {
            animation: chomp-card-shake 2s ease-in-out;
        }

        /* Bat smash animation */
        @keyframes bat-drop-in {
            0% { transform: translateY(-200%) rotate(0deg); }
            35% { transform: translateY(-10%) rotate(0deg); }
            45% { transform: translateY(0%) rotate(45deg); }
            55% { transform: translateY(0%) rotate(-15deg); }
            65% { transform: translateY(0%) rotate(10deg); }
            100% { transform: translateY(-200%) rotate(0deg); }
        }

        @keyframes bat-card-shatter {
            0% { transform: scale(1); opacity: 1; clip-path: inset(0); }
            40% { transform: scale(1); opacity: 1; clip-path: inset(0); }
            50% { transform: scale(1.05); opacity: 0.9; }
            60% { transform: scale(0.95) rotate(2deg); opacity: 0.6; clip-path: polygon(0% 0%, 60% 0%, 70% 50%, 30% 100%, 0% 100%); }
            75% { transform: scale(0.9) rotate(-1deg); opacity: 0.3; clip-path: polygon(10% 10%, 50% 0%, 60% 60%, 20% 80%); }
            100% { transform: scale(1); opacity: 1; clip-path: inset(0); }
        }

        .beaver-bat .beaver-actor {
            top: 0;
            left: 50%;
            margin-left: -40px;
            animation: bat-drop-in 2s ease-in-out forwards;
        }

        .beaver-bat .beaver-bat-weapon {
            position: absolute;
            top: 15%;
            left: 50%;
            margin-left: 10px;
            font-size: 50px;
            animation: bat-drop-in 2s ease-in-out forwards;
        }

        .beaver-bat .now-playing-card {
            animation: bat-card-shatter 2s ease-in-out;
        }
    </style>
    """)

    with ui.column().classes("w-full max-w-3xl mx-auto p-8 gap-6"):
        with ui.column().classes("items-center gap-1"):
            ui.label("🦫").classes("text-5xl")
            ui.label("VERZOEKJESBEVER").classes("text-2xl font-extrabold tracking-wide text-white")
            ui.label("REQUEST PARTY").classes("text-xs tracking-[0.3em] text-green-400")

        if not svc.has_session:
            with ui.card().classes("w-full bg-gray-800 rounded-xl p-8 text-center"):
                ui.label("🦫").classes("text-4xl")
                ui.label("Waiting for DJ to start the party").classes("text-xl text-gray-400 mt-2")
                ui.label("Check back soon!").classes("text-gray-500")
            return

        @ui.refreshable
        def playlist_display():
            current = svc.get_currently_playing()

            if current:
                with ui.element("div").classes("now-playing-wrapper w-full"):
                    with ui.card().classes("w-full bg-green-600 rounded-xl p-5 now-playing-card"):
                        ui.label("NOW PLAYING").classes("text-xs tracking-[0.2em] text-white/70")
                        with ui.row().classes("items-center gap-5 mt-2"):
                            if current.album_art_url:
                                ui.image(current.album_art_url).classes("w-20 h-20 rounded-lg")
                            with ui.column().classes("gap-0"):
                                ui.label(current.track_name).classes("text-2xl font-extrabold text-white")
                                ui.label(current.artist).classes("text-lg text-white/85")
                                if current.requester:
                                    ui.label(f"🎤 Requested by {current.requester}").classes(
                                        "text-sm text-white/60 mt-1"
                                    )
            else:
                with ui.card().classes("w-full bg-gray-800 rounded-xl p-8 text-center"):
                    ui.label("🦫").classes("text-4xl")
                    ui.label("No song playing yet").classes("text-xl text-gray-400 mt-2")
                    ui.label("Make a request!").classes("text-gray-500")

            queue = svc.get_queue()
            if queue:
                ui.label("UP NEXT").classes("text-xs tracking-[0.2em] text-gray-500 mt-4")
                with ui.card().classes("w-full bg-white/5 rounded-xl p-1"):
                    for i, item in enumerate(queue):
                        border = "border-b border-white/5" if i < len(queue) - 1 else ""
                        with ui.row().classes(f"items-center gap-3 px-4 py-3 {border}"):
                            ui.label(str(i + 1)).classes("text-green-400 font-extrabold text-lg w-7 text-center")
                            if item.album_art_url:
                                ui.image(item.album_art_url).classes("w-11 h-11 rounded-md")
                            with ui.column().classes("flex-grow gap-0"):
                                ui.label(item.track_name).classes("text-white font-semibold text-base")
                                ui.label(item.artist).classes("text-gray-400 text-sm")
                                if item.requester:
                                    ui.label(f"🎤 {item.requester}").classes("text-orange-400 text-xs mt-0.5")

        playlist_display()

        BEAVER_ANIMATION_JS = """
(function() {
    const wrapper = document.querySelector('.now-playing-wrapper');
    if (!wrapper) return;

    // Remove any existing overlay
    const existing = wrapper.querySelector('.beaver-overlay');
    if (existing) existing.remove();

    // Pick random animation
    const animations = ['beaver-chomp', 'beaver-bat'];
    const pick = animations[Math.floor(Math.random() * animations.length)];

    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'beaver-overlay ' + pick;

    const beaver = document.createElement('span');
    beaver.className = 'beaver-actor';
    beaver.textContent = '🦫';
    overlay.appendChild(beaver);

    if (pick === 'beaver-bat') {
        const bat = document.createElement('span');
        bat.className = 'beaver-bat-weapon';
        bat.textContent = '🏏';
        overlay.appendChild(bat);
    }

    wrapper.classList.add(pick);
    wrapper.appendChild(overlay);

    setTimeout(() => {
        overlay.remove();
        wrapper.classList.remove(pick);
    }, 2200);
})();
"""

        local_version = {"v": svc.version}
        local_skip_version = {"v": svc.last_skip_version}

        async def check_updates():
            if svc.version != local_version["v"]:
                skip_happened = (
                    svc.beaver_enabled
                    and svc.last_skip_version > local_skip_version["v"]
                )
                local_version["v"] = svc.version
                local_skip_version["v"] = svc.last_skip_version

                if skip_happened:
                    await ui.run_javascript(BEAVER_ANIMATION_JS)
                    await asyncio.sleep(2.2)

                playlist_display.refresh()

        ui.timer(1.0, check_updates)
