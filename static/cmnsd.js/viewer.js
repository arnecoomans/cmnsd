// A zoomable image viewer for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// A container marked data-cmnsd-viewer with an <img data-viewer-image>
// inside: the image fits at first, then
//   scroll (wheel, a trackpad's two fingers)  moves the image
//   pinch (trackpad, touch), Ctrl/Cmd + scroll  zooms around the pointer
//   drag (mouse / touch)  pans
//   [data-viewer-zoom-in] / [data-viewer-zoom-out] / [data-viewer-fit] /
//   [data-viewer-rotate]  buttons anywhere inside the container
//   Alt + arrows          pan, Alt + plus / minus zoom, Alt + 0 fit, Alt + r
//                         rotate - Alt, so they also work while typing in
//                         a text field next to the image (a transcribe
//                         page)
// The view (zoom, position, rotation) is the viewer's own - the image file
// is untouched. Used by fmly's transcribe page and the lightbox.
//
// data-viewer-original="<url>" on the container: a sharper version of the
// image (e.g. the original file behind a screen-sized one). Loaded once
// the zoom goes past the shown image's own pixels, then swapped in at the
// same view - so a page shows fast, and detail comes when it's asked for.
// The container gets .is-loading meanwhile.
//
// Crop mode - data-viewer-crop on the container (a frame, e.g. square):
// what's visible in the frame is the crop. Inputs [data-crop="x|y|w|h"] in
// the surrounding form hold it as fractions of the image (0-1, the image as
// shown); they set the first view, and every move or zoom writes them back
// (the part outside the image left out). Empty inputs: the whole image,
// fitted. An input [data-crop="rotate"] holds the turn (0/90/180/270,
// clockwise): the rotate button turns the image and the crop is taken on
// the turned image (fractions of it); without that input, no turning.
// Radios [data-crop-source="<image url>"] in the form switch the image: the
// new one shows whole and unturned (its crop written as the whole image);
// [data-crop-caption] gets the radio's data-crop-caption-text / -url.

import { once } from './dom.js';

const SELECTOR = '[data-cmnsd-viewer]';
const MIN = 0.5;   // times the fitted size
const MAX = 12;
const STEP = 1.25;
const PAN = 60;

function bindViewer(viewer) {
  if (!once(viewer, 'viewer')) return;
  const image = viewer.querySelector('[data-viewer-image]');
  if (!image) return;
  // The view: where the image's centre is (viewer coordinates), its scale
  // and rotation. The image scales and rotates around its own centre, so
  // the centre is what moves - everything else follows from it.
  const view = { cx: 0, cy: 0, scale: 1, rotate: 0, fitted: 1 };
  const pointers = new Map();
  let pinch = null;

  const cropping = viewer.hasAttribute('data-viewer-crop');
  const form = viewer.closest('form');
  const cropInput = (key) => (form || viewer).querySelector(`[data-crop="${key}"]`);

  // The image's size as shown: width and height swap when it's turned sideways.
  const shownSize = () => (view.rotate % 180
    ? [image.naturalHeight, image.naturalWidth]
    : [image.naturalWidth, image.naturalHeight]);

  // Crop mode: the frame's part of the (turned) image, as fractions
  // (clipped to the image), into the crop inputs - and the turn.
  const writeCrop = () => {
    const box = viewer.getBoundingClientRect();
    const [shownWidth, shownHeight] = shownSize();
    const width = shownWidth * view.scale;
    const height = shownHeight * view.scale;
    if (!width || !height) return;
    const left = view.cx - width / 2;
    const top = view.cy - height / 2;
    const x1 = Math.max(0, -left / width);
    const y1 = Math.max(0, -top / height);
    const x2 = Math.min(1, (box.width - left) / width);
    const y2 = Math.min(1, (box.height - top) / height);
    const values = { x: x1, y: y1, w: Math.max(0, x2 - x1), h: Math.max(0, y2 - y1) };
    Object.entries(values).forEach(([key, value]) => {
      const input = cropInput(key);
      // Rounded down: x + w never ends up just past the image's edge.
      if (input) input.value = (Math.floor(value * 1e5) / 1e5).toString();
    });
    const turn = cropInput('rotate');
    if (turn) turn.value = String(view.rotate);
  };

  const apply = () => {
    const x = view.cx - image.naturalWidth / 2;
    const y = view.cy - image.naturalHeight / 2;
    image.style.transform = `translate(${x}px, ${y}px) scale(${view.scale}) rotate(${view.rotate}deg)`;
    if (cropping) writeCrop();
  };

  // Crop mode: the crop in the inputs - read before the first fit, which
  // writes the whole image into them.
  const readCrop = () => ['x', 'y', 'w', 'h'].map((key) => parseFloat(cropInput(key)?.value));
  const storedCrop = cropping ? readCrop() : null;
  // Crop mode: turning only with a place to keep the turn.
  const canTurn = !cropping || Boolean(cropInput('rotate'));
  if (cropping && canTurn) view.rotate = (parseInt(cropInput('rotate').value, 10) || 0) % 360;

  // Crop mode: show a crop (default: the inputs' current one) filling the frame.
  const showCrop = (crop = readCrop()) => {
    const [x, y, w, h] = crop;
    if ([x, y, w, h].some((value) => Number.isNaN(value)) || !w || !h) return false;
    const box = viewer.getBoundingClientRect();
    const [shownWidth, shownHeight] = shownSize();
    // Filling the frame (a crop of another shape shows its centre) - as a
    // square thumbnail of it does.
    view.scale = Math.max(box.width / (w * shownWidth), box.height / (h * shownHeight));
    const width = shownWidth * view.scale;
    const height = shownHeight * view.scale;
    // The crop's centre in the frame's centre.
    view.cx = box.width / 2 - (x + w / 2) * width + width / 2;
    view.cy = box.height / 2 - (y + h / 2) * height + height / 2;
    apply();
    return true;
  };

  // Fit: the whole image in the viewer, centred (taking the rotation into account).
  const fit = () => {
    const box = viewer.getBoundingClientRect();
    const sideways = view.rotate % 180 !== 0;
    const width = sideways ? image.naturalHeight : image.naturalWidth;
    const height = sideways ? image.naturalWidth : image.naturalHeight;
    if (!width || !height) return;
    view.scale = view.fitted = Math.min(box.width / width, box.height / height) * 0.96;
    view.cx = box.width / 2;
    view.cy = box.height / 2;
    apply();
  };

  // Zoom by `factor` keeping the point (px, py) - viewer coordinates - in
  // place: the centre moves away from / towards that point. From half the
  // fitted size up to MAX times the image's own pixels.
  const zoom = (factor, px, py) => {
    const box = viewer.getBoundingClientRect();
    const x = px ?? box.width / 2;
    const y = py ?? box.height / 2;
    const next = Math.min(Math.max(MAX, view.fitted), Math.max(view.fitted * MIN, view.scale * factor));
    const ratio = next / view.scale;
    view.cx = x + (view.cx - x) * ratio;
    view.cy = y + (view.cy - y) * ratio;
    view.scale = next;
    apply();
    sharpen();
  };

  // A sharper version (data-viewer-original): fetched once the zoom goes
  // past the image's own pixels, swapped in at the same size on screen.
  const sharper = viewer.dataset.viewerOriginal;
  let sharpening = false;
  function sharpen() {
    if (!sharper || sharpening || view.scale <= 1) return;
    sharpening = true;
    viewer.classList.add('is-loading');
    const next = new Image();
    next.onload = () => {
      const ratio = image.naturalWidth / next.naturalWidth;
      const swap = () => {
        // Same size on screen: the new image has more pixels per point.
        view.scale *= ratio;
        view.fitted *= ratio;
        apply();
        viewer.classList.remove('is-loading');
      };
      image.addEventListener('load', swap, { once: true });
      image.src = next.src;   // from the cache - loads at once
    };
    next.onerror = () => viewer.classList.remove('is-loading');
    next.src = sharper;
  }

  const rotate = () => {
    if (!canTurn) return;   // crop mode without a turn input: the image as shown
    view.rotate = (view.rotate + 90) % 360;
    fit();   // crop mode: the whole turned image, written as the new crop
  };

  image.style.transformOrigin = 'center center';
  // The image's own box is its natural size; transforms do the rest.
  image.style.position = 'absolute';
  image.style.left = '0';
  image.style.top = '0';
  image.style.maxWidth = 'none';
  image.draggable = false;
  const start = () => {
    const crop = storedCrop;
    fit();   // also sets the zoom range
    if (cropping) showCrop(crop);
  };
  if (image.complete && image.naturalWidth) start(); else image.addEventListener('load', start, { once: true });

  // Crop mode: another image chosen (a radio with data-crop-source) - shown
  // whole and unturned once it has loaded.
  if (cropping && form) {
    form.addEventListener('change', (event) => {
      const source = event.target.closest('[data-crop-source]');
      if (!source || !source.checked) return;
      const caption = form.querySelector('[data-crop-caption]');
      if (caption) {
        caption.textContent = source.dataset.cropCaptionText || '';
        if (source.dataset.cropCaptionUrl) caption.href = source.dataset.cropCaptionUrl;
      }
      image.addEventListener('load', () => {
        view.rotate = 0;
        fit();   // writes the whole image as the crop
      }, { once: true });
      image.src = source.dataset.cropSource;
    });
  }
  // Crop mode keeps the crop on a resize (refitting would replace it).
  window.addEventListener('resize', () => (cropping ? showCrop() || fit() : fit()));

  // Scrolling moves the image, as a page would; zooming is a pinch - which a
  // trackpad sends as a wheel event with ctrlKey - or Ctrl/Cmd + scroll.
  viewer.addEventListener('wheel', (event) => {
    event.preventDefault();
    // deltaMode 1: lines (some mice), not pixels.
    const unit = event.deltaMode === 1 ? 16 : 1;
    if (event.ctrlKey || event.metaKey) {
      const box = viewer.getBoundingClientRect();
      // Smooth for a trackpad's small steps, a fixed step for a mouse's notches.
      const factor = Math.abs(event.deltaY * unit) < 50 ? Math.exp(-event.deltaY * unit * 0.01) : (event.deltaY < 0 ? STEP : 1 / STEP);
      zoom(factor, event.clientX - box.left, event.clientY - box.top);
      return;
    }
    // Shift + a mouse wheel: sideways.
    const dx = event.shiftKey && !event.deltaX ? event.deltaY : event.deltaX;
    const dy = event.shiftKey && !event.deltaX ? 0 : event.deltaY;
    view.cx -= dx * unit;
    view.cy -= dy * unit;
    apply();
  }, { passive: false });

  viewer.addEventListener('pointerdown', (event) => {
    if (event.target.closest('button, a')) return;
    viewer.setPointerCapture(event.pointerId);
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    viewer.classList.add('is-dragging');
  });
  viewer.addEventListener('pointermove', (event) => {
    const last = pointers.get(event.pointerId);
    if (!last) return;
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      const distance = Math.hypot(a.x - b.x, a.y - b.y);
      const box = viewer.getBoundingClientRect();
      if (pinch) zoom(distance / pinch, (a.x + b.x) / 2 - box.left, (a.y + b.y) / 2 - box.top);
      pinch = distance;
      return;
    }
    view.cx += event.clientX - last.x;
    view.cy += event.clientY - last.y;
    apply();
  });
  const release = (event) => {
    pointers.delete(event.pointerId);
    if (pointers.size < 2) pinch = null;
    if (!pointers.size) viewer.classList.remove('is-dragging');
  };
  viewer.addEventListener('pointerup', release);
  viewer.addEventListener('pointercancel', release);

  viewer.addEventListener('click', (event) => {
    const button = event.target.closest('[data-viewer-zoom-in], [data-viewer-zoom-out], [data-viewer-fit], [data-viewer-rotate]');
    if (!button) return;
    event.preventDefault();
    if (button.hasAttribute('data-viewer-zoom-in')) zoom(STEP);
    else if (button.hasAttribute('data-viewer-zoom-out')) zoom(1 / STEP);
    else if (button.hasAttribute('data-viewer-fit')) fit();
    else rotate();
  });

  document.addEventListener('keydown', (event) => {
    if (!event.altKey || !viewer.isConnected) return;
    const actions = {
      ArrowLeft: () => { view.cx += PAN; apply(); },
      ArrowRight: () => { view.cx -= PAN; apply(); },
      ArrowUp: () => { view.cy += PAN; apply(); },
      ArrowDown: () => { view.cy -= PAN; apply(); },
    };
    const byCode = { Equal: () => zoom(STEP), NumpadAdd: () => zoom(STEP), Minus: () => zoom(1 / STEP), NumpadSubtract: () => zoom(1 / STEP), Digit0: fit, KeyR: rotate };
    const action = actions[event.key] || byCode[event.code];
    if (!action) return;
    event.preventDefault();
    action();
  });
}

export function bindViewers(root) {
  root.querySelectorAll(SELECTOR).forEach(bindViewer);
}
