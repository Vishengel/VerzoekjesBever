// Run a chomp/bat "destroy" animation over `wrapper`. The wrapper must be
// position:relative (the overlay is absolute inset:0) and carry the card-shake
// target class the CSS keyframes hook onto.
function runBeaverDestroy(wrapper) {
    if (!wrapper) return;

    const existing = wrapper.querySelector('.beaver-overlay');
    if (existing) existing.remove();

    const animations = ['beaver-chomp', 'beaver-bat'];
    const pick = animations[Math.floor(Math.random() * animations.length)];

    const overlay = document.createElement('div');
    overlay.className = 'beaver-overlay ' + pick;

    const beaver = document.createElement('span');
    beaver.className = 'beaver-actor';
    const img = document.createElement('img');
    img.src = '/static/beaver.svg';
    img.style.width = '80px';
    img.style.height = '80px';
    beaver.appendChild(img);
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

// Skip: beaver destroys the now-playing card (the track that just left).
function triggerBeaverAnimation() {
    runBeaverDestroy(document.querySelector('.now-playing-wrapper'));
}

// Shame-delete: if the removed song is one of the always-visible prominent
// cards, chomp it directly; otherwise the row may be off-screen / scrolling /
// hidden, so the beaver attacks the whole COMING UP box instead.
function triggerBeaverDeleteAnimation(uid) {
    const sel = '.prominent-cards [data-uid="' + CSS.escape(uid) + '"]';
    const card = document.querySelector(sel);
    if (card) {
        runBeaverDestroy(card);
        return;
    }
    runBeaverBoxAttack();
}

// Beaver attacks the scrolling queue box: pause the creep, shake + chomp the
// region, then resume. Robust regardless of where the deleted row sat.
function runBeaverBoxAttack() {
    const region = document.querySelector('.scroll-region');
    if (!region) return;
    const track = document.querySelector('.scroll-track');
    if (track) track.classList.add('paused');
    region.classList.add('beaver-delete-target');
    runBeaverDestroy(region);
    setTimeout(() => {
        region.classList.remove('beaver-delete-target');
        if (track) track.classList.remove('paused');
    }, 2200);
}

// The single always-visible prominent up-next card (the new #1). Zone-based
// animations target this stable element, never a scrolling/off-screen row.
function _promCard() {
    return document.querySelector('.prominent-cards [data-uid]');
}

// Move-to-top (or a priority add with the beaver disabled): golden glow on the
// prominent card, no beaver actor.
function triggerPromoteGlow() {
    const card = _promCard();
    if (!card) return;
    card.style.animation = 'priority-glow 0.6s ease-in-out 3';
    setTimeout(function() { card.style.animation = ''; }, 2000);
}

// Priority add (beaver on): beaver reveals the new #1 on the prominent card,
// wearing a crown, then a golden glow. Self-applies/cleans up its own classes.
function triggerBeaverPromote() {
    const card = _promCard();
    if (!card) return;  // queue empty / card not rendered yet

    const existing = document.querySelector('.beaver-add-overlay');
    if (existing) existing.remove();

    const variants = ['carry', 'toss', 'build'];
    const pick = variants[Math.floor(Math.random() * variants.length)];
    const duration = 1.5;
    const keyframes = {
        carry: { beaver: 'carry-beaver-slide', card: 'carry-card-reveal' },
        toss: { beaver: 'toss-beaver-popup', card: 'toss-card-reveal' },
        build: { beaver: 'build-beaver-hammer', card: 'build-card-reveal' }
    };

    const overlay = document.createElement('div');
    overlay.className = 'beaver-add-overlay beaver-add-' + pick;
    const beaver = document.createElement('span');
    beaver.className = 'beaver-actor';
    beaver.style.animation = keyframes[pick].beaver + ' ' + duration + 's ease-in-out forwards';
    const img = document.createElement('img');
    img.className = 'beaver-emoji';
    img.src = '/static/beaver.svg';
    img.style.width = '80px';
    img.style.height = '80px';
    beaver.appendChild(img);
    const crown = document.createElement('span');
    crown.className = 'beaver-accessory';
    crown.style.top = '-23px';
    crown.textContent = '👑';
    beaver.appendChild(crown);
    overlay.appendChild(beaver);

    // The prominent card is position:relative (beaver-delete-target), so the
    // inset:0 overlay anchors over it.
    card.appendChild(overlay);
    card.classList.add('beaver-incoming');
    card.style.animation = keyframes[pick].card + ' ' + duration + 's ease-in-out forwards';

    setTimeout(function() {
        card.classList.remove('beaver-incoming');
        card.style.animation = 'priority-glow 0.6s ease-in-out 3';
        setTimeout(function() {
            card.style.animation = '';
            overlay.remove();
        }, 2000);
    }, (duration + 0.2) * 1000);
}

// Regular add (beaver on): the new song lands deep in the queue (off-screen),
// so the beaver tosses it onto the COMING UP box. Pause the creep, pop a beaver
// over the box with a green pulse, then resume.
function triggerBeaverBoxAdd() {
    const region = document.querySelector('.scroll-region');
    if (!region) { triggerBeaverPromote(); return; }  // tiny queue: no box

    const track = document.querySelector('.scroll-track');
    if (track) track.classList.add('paused');

    const existing = region.querySelector('.beaver-add-overlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.className = 'beaver-add-overlay beaver-add-toss';
    const beaver = document.createElement('span');
    beaver.className = 'beaver-actor';
    beaver.style.animation = 'toss-beaver-popup 2.2s ease-in-out forwards';
    const img = document.createElement('img');
    img.src = '/static/beaver.svg';
    img.style.width = '80px';
    img.style.height = '80px';
    beaver.appendChild(img);
    overlay.appendChild(beaver);
    region.appendChild(overlay);
    region.classList.add('box-add');

    setTimeout(function() {
        region.classList.remove('box-add');
        overlay.remove();
        if (track) track.classList.remove('paused');
    }, 2400);
}

function triggerShameOverlay(message) {
    var existing = document.querySelector('.shame-overlay');
    if (existing) existing.remove();

    var overlay = document.createElement('div');
    overlay.className = 'shame-overlay';
    overlay.textContent = message;
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100%';
    overlay.style.zIndex = '200';
    overlay.style.padding = '32px 24px';
    overlay.style.textAlign = 'center';
    overlay.style.fontSize = '2.5rem';
    overlay.style.fontWeight = '800';
    overlay.style.color = '#ffffff';
    overlay.style.background = 'rgba(13, 13, 26, 0.92)';
    overlay.style.borderBottom = '4px solid #4ade80';
    overlay.style.backdropFilter = 'blur(6px)';
    overlay.style.boxShadow = '0 8px 32px rgba(0,0,0,0.5)';

    document.body.appendChild(overlay);

    var anim = overlay.animate(
        [
            { opacity: 0, transform: 'translateY(-40px)' },
            { opacity: 1, transform: 'translateY(0)', offset: 0.08 },
            { opacity: 1, transform: 'translateY(0)', offset: 0.85 },
            { opacity: 0, transform: 'translateY(-40px)' }
        ],
        { duration: 6000, easing: 'ease-in-out' }
    );

    anim.onfinish = function () { overlay.remove(); };
}
