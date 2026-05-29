function triggerBeaverAnimation() {
    const wrapper = document.querySelector('.now-playing-wrapper');
    if (!wrapper) return;

    const existing = wrapper.querySelector('.beaver-overlay');
    if (existing) existing.remove();

    const animations = ['beaver-chomp', 'beaver-bat'];
    const pick = animations[Math.floor(Math.random() * animations.length)];

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
}
