// Drives the audience billboard scroll by pixels (scrollTop) via rAF, rather
// than a CSS transform. Pixel scrolling reads the live layout each frame, so
// inserting a song below the current position doesn't shift what's on screen —
// no jump. The DOM is two equal halves (.scroll-real + .scroll-clone); we wrap
// scrollTop after one half so the loop is seamless. Driven from Python:
// setupAudienceScroll() once on load; updateAudienceScroll() is a no-op kept as
// a stable hook. pause/resumeAudienceScroll() let the beaver freeze the creep.

const BILLBOARD_PX_PER_SEC = 22; // slow movie-credits creep

let _billboardPaused = false;
let _billboardLastTs = null;

function pauseAudienceScroll() { _billboardPaused = true; }
function resumeAudienceScroll() { _billboardPaused = false; }

// No-op: the rAF loop reads heights live, so content changes need no nudge.
function updateAudienceScroll() {}

function setupAudienceScroll() {
  const region = document.querySelector('.scroll-region');
  const track = document.querySelector('.scroll-track');
  if (!region || !track || region.dataset.billboardBound) return;
  region.dataset.billboardBound = '1';

  // Pause on touch/hover so a phone viewer can read without fighting the creep.
  region.addEventListener('pointerdown', pauseAudienceScroll);
  region.addEventListener('pointerup', resumeAudienceScroll);
  region.addEventListener('pointerleave', resumeAudienceScroll);
  region.addEventListener('mouseenter', pauseAudienceScroll);
  region.addEventListener('mouseleave', resumeAudienceScroll);

  function step(ts) {
    requestAnimationFrame(step);
    const real = region.querySelector('.scroll-real');
    if (!real) return;

    const halfHeight = real.scrollHeight;          // one copy of the rows
    const viewHeight = region.clientHeight;

    // Fits on screen: no scroll, hide the clone + loop marker (no seam to show).
    if (halfHeight <= viewHeight + 1) {
      if (track.classList.contains('scrolling')) {
        track.classList.remove('scrolling');
      }
      region.scrollTop = 0;
      _billboardLastTs = ts;
      return;
    }
    if (!track.classList.contains('scrolling')) {
      track.classList.add('scrolling');
    }

    if (_billboardPaused || _billboardLastTs === null) {
      _billboardLastTs = ts;
      return;
    }
    const dt = (ts - _billboardLastTs) / 1000;
    _billboardLastTs = ts;

    let top = region.scrollTop + BILLBOARD_PX_PER_SEC * dt;
    if (top >= halfHeight) top -= halfHeight;   // seamless wrap into the clone
    region.scrollTop = top;
  }
  requestAnimationFrame(step);
}
