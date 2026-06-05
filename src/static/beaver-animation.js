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

// Shame-delete: beaver destroys the specific queue row being removed.
function triggerBeaverDeleteAnimation(uid) {
    const row = document.querySelector('[data-uid="' + CSS.escape(uid) + '"]');
    runBeaverDestroy(row);
}

function triggerPriorityGlow() {
    var target = document.querySelector('.priority-glow-target');
    if (!target) return;
    target.style.animation = 'priority-glow 0.6s ease-in-out 3';
    setTimeout(function() {
        target.style.animation = '';
    }, 2000);
}

function triggerBeaverAddAnimation(isPriority) {
    var wrapper = document.querySelector('.queue-add-target');
    if (!wrapper) return;

    var card = wrapper.querySelector('.beaver-incoming');
    if (!card) return;

    var existing = document.querySelector('.beaver-add-overlay');
    if (existing) existing.remove();

    var variants = ['carry', 'toss', 'build'];
    var pick = variants[Math.floor(Math.random() * variants.length)];
    var duration = isPriority ? 1.5 : 2.2;

    var keyframes = {
        carry: { beaver: 'carry-beaver-slide', card: 'carry-card-reveal' },
        toss: { beaver: 'toss-beaver-popup', card: 'toss-card-reveal' },
        build: { beaver: 'build-beaver-hammer', card: 'build-card-reveal' }
    };

    var overlay = document.createElement('div');
    overlay.className = 'beaver-add-overlay beaver-add-' + pick;

    var beaver = document.createElement('span');
    beaver.className = 'beaver-actor';
    beaver.style.animation = keyframes[pick].beaver + ' ' + duration + 's ease-in-out forwards';
    var beaverEmoji = document.createElement('img');
    beaverEmoji.className = 'beaver-emoji';
    beaverEmoji.src = '/static/beaver.svg';
    beaverEmoji.style.width = '80px';
    beaverEmoji.style.height = '80px';
    beaver.appendChild(beaverEmoji);
    if (isPriority) {
        var accessory = document.createElement('span');
        accessory.className = 'beaver-accessory';
        if (Math.random() >= 0.1) {
            accessory.style.top = '-23px';
        }
        accessory.textContent = '👑';
        beaver.appendChild(accessory);
    }
    overlay.appendChild(beaver);
    wrapper.appendChild(overlay);

    card.style.animation = keyframes[pick].card + ' ' + duration + 's ease-in-out forwards';

    var cleanupDelay = (duration + 0.2) * 1000;

    if (isPriority) {
        setTimeout(function() {
            card.classList.remove('beaver-incoming');
            card.style.animation = 'priority-glow 0.6s ease-in-out 3';
            setTimeout(function() {
                card.style.animation = '';
                overlay.remove();
            }, 2000);
        }, cleanupDelay);
    } else {
        setTimeout(function() {
            card.classList.remove('beaver-incoming');
            card.style.animation = '';
            overlay.remove();
        }, cleanupDelay);
    }
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
