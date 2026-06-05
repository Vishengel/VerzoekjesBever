// Manages the audience billboard scroll: sets speed from row count, disables
// the animation when content fits, and pauses on touch/hover. Driven from the
// Python render via ui.run_javascript('updateAudienceScroll()').

const BILLBOARD_PX_PER_SEC = 22; // slow movie-credits creep

function _billboardEls() {
  const region = document.querySelector('.scroll-region');
  const track = document.querySelector('.scroll-track');
  const real = document.querySelector('.scroll-real'); // the live rows half
  return { region, track, real };
}

function updateAudienceScroll() {
  const { region, track, real } = _billboardEls();
  if (!region || !track || !real) return;

  // real = one copy of the rows; track = real + clone. Compare a single copy's
  // height to the visible region to decide whether scrolling is needed.
  const contentHeight = real.scrollHeight;
  const visibleHeight = region.clientHeight;

  if (contentHeight <= visibleHeight + 1) {
    track.classList.remove('scrolling');
    track.style.animationDuration = '';
    return;
  }

  const durationSec = contentHeight / BILLBOARD_PX_PER_SEC;
  track.style.animationDuration = durationSec.toFixed(2) + 's';
  track.classList.add('scrolling');
}

function setupAudienceScroll() {
  const { region, track } = _billboardEls();
  if (!region || !track || region.dataset.billboardBound) return;
  region.dataset.billboardBound = '1';

  const pause = () => track.classList.add('paused');
  const resume = () => track.classList.remove('paused');
  region.addEventListener('pointerdown', pause);
  region.addEventListener('pointerup', resume);
  region.addEventListener('pointerleave', resume);
  region.addEventListener('mouseenter', pause);
  region.addEventListener('mouseleave', resume);
}
