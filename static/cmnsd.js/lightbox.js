// A lightbox for images, for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// A link marked data-cmnsd-lightbox (its href: the original file) opens the
// image full-screen in a native <dialog>, in a zoomable viewer (viewer.js:
// wheel, drag, pinch, buttons) instead of navigating to the bare file.
// The link's data:
//   data-lightbox-src     what shows first (a screen-sized version)
//   data-lightbox-zoom    a sharper version, loaded when zoomed in past
//                         the first one (viewer.js data-viewer-original)
//   data-lightbox-title   the caption; data-lightbox-page its link
//   data-lightbox-items   "<selector>" of a JSON script with a sequence
//                         [{title, src, zoom, file, page}] - then ‹ / ›
//                         and the ← / → keys step through it, starting at
//                         the item whose file is the link's href (the
//                         gallery keeps that current, gallery.js)
//   data-lightbox-text-*  labels: close, original, previous, next,
//                         zoom-in, zoom-out, fit, rotate
// Esc or the close button close it (not a click beside the image: the whole
// area drags the image). A click with a modifier key (new tab) and no JS
// keep the plain link to the file.

import { enhance } from './enhance.js';
import { dbg } from './context.js';

const SELECTOR = 'a[data-cmnsd-lightbox]';

function sequence(link) {
  const selector = link.dataset.lightboxItems;
  const script = selector && document.querySelector(selector);
  if (script) {
    try {
      const items = JSON.parse(script.textContent);
      if (Array.isArray(items) && items.length) return items;
    } catch (err) {
      dbg('lightbox: bad items', err);
    }
  }
  return [{
    title: link.dataset.lightboxTitle || '',
    src: link.dataset.lightboxSrc || link.href,
    zoom: link.dataset.lightboxZoom || '',
    file: link.href,
    page: link.dataset.lightboxPage || '',
  }];
}

function button(attribute, label, icon) {
  return `<button type="button" ${attribute} title="${label}" aria-label="${label}"><i class="bi bi-${icon}"></i></button>`;
}

function open(link) {
  const text = (key, fallback) => link.dataset[`lightboxText${key}`] || fallback;
  const items = sequence(link);
  const absolute = (url) => new URL(url, window.location.href).href;
  let current = Math.max(0, items.findIndex((item) => absolute(item.file) === link.href));

  const dialog = document.createElement('dialog');
  dialog.className = 'cmnsd-lightbox';
  document.body.append(dialog);

  function show(index) {
    current = (index + items.length) % items.length;
    const item = items[current];
    const many = items.length > 1;
    dialog.innerHTML = `
      <div class="cmnsd-lightbox__viewer" data-cmnsd-viewer>
        <img data-viewer-image alt="">
        <div class="cmnsd-lightbox__bar">
          ${many ? button('data-lightbox-previous', text('Previous', 'Previous'), 'chevron-left') : ''}
          ${many ? `<span class="cmnsd-lightbox__counter">${current + 1} / ${items.length}</span>` : ''}
          ${many ? button('data-lightbox-next', text('Next', 'Next'), 'chevron-right') : ''}
          <a class="cmnsd-lightbox__caption"></a>
          <span class="cmnsd-lightbox__tools">
            ${button('data-viewer-zoom-in', text('ZoomIn', 'Zoom in'), 'zoom-in')}
            ${button('data-viewer-zoom-out', text('ZoomOut', 'Zoom out'), 'zoom-out')}
            ${button('data-viewer-fit', text('Fit', 'Whole image'), 'arrows-angle-contract')}
            ${button('data-viewer-rotate', text('Rotate', 'Turn a quarter'), 'arrow-clockwise')}
            <a class="cmnsd-lightbox__original" target="_blank" rel="noopener" title="${text('Original', 'Open original')}" aria-label="${text('Original', 'Open original')}"><i class="bi bi-box-arrow-up-right"></i></a>
            ${button('data-lightbox-close', text('Close', 'Close'), 'x-lg')}
          </span>
        </div>
      </div>`;
    // Set as properties, not in the HTML: titles and urls stay text.
    const viewer = dialog.querySelector('[data-cmnsd-viewer]');
    if (item.zoom) viewer.dataset.viewerOriginal = item.zoom;
    const image = dialog.querySelector('[data-viewer-image]');
    image.alt = item.title || '';
    image.src = item.src;
    const caption = dialog.querySelector('.cmnsd-lightbox__caption');
    caption.textContent = item.title || '';
    if (item.page) caption.href = item.page;
    dialog.querySelector('.cmnsd-lightbox__original').href = item.file;
    enhance(dialog);   // the viewer (viewer.js) - after showModal: it measures its frame
  }

  const close = () => {
    if (dialog.open) dialog.close();
    dialog.remove();
  };
  dialog.addEventListener('close', close);
  dialog.addEventListener('click', (event) => {
    if (event.target.closest('[data-lightbox-close]')) close();
    else if (event.target.closest('[data-lightbox-previous]')) show(current - 1);
    else if (event.target.closest('[data-lightbox-next]')) show(current + 1);
  });
  dialog.addEventListener('keydown', (event) => {
    if (event.altKey) return;   // the viewer's own keys
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault();
      event.stopPropagation();   // not the page's gallery as well
      if (items.length > 1) show(current + (event.key === 'ArrowLeft' ? -1 : 1));
    }
  });
  dialog.showModal();
  show(current);
}

export function bindLightboxes(root) {
  root.addEventListener('click', (event) => {
    const link = event.target.closest(SELECTOR);
    if (!link || event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
    event.preventDefault();
    open(link);
  });
}
