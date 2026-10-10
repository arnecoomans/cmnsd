// Image browsing for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// A container marked data-cmnsd-gallery holds the main image
// ([data-gallery-image], inside a link [data-gallery-link]) and a
// <script type="application/json" id="…-items"> (Django json_script) with
// the sequence: [{title, src, file, page}, ...]; data-gallery-start="<n>"
// on the container: the one shown, whose page this is (default the
// first). ‹ / › ([data-gallery-previous] / [data-gallery-next]) and the
// ← / → keys step through it, in place - the image, its link (to the
// original file), a counter and a caption (linking to that item's page)
// follow. [data-gallery-open] - a link to the shown item's own page - is
// hidden while the start item (the page you're on) shows. Elements elsewhere marked data-gallery-show="<index>" (the parts
// thumbnails) show that item instead of navigating. Without JS: no
// buttons, and those thumbnails are plain links.

import { closest, once } from './dom.js';
import { dbg } from './context.js';

const SELECTOR = '[data-cmnsd-gallery]';

function bindGallery(gallery) {
  if (!once(gallery, 'gallery')) return;
  const data = gallery.querySelector('script[type="application/json"]');
  if (!data) return;
  let items;
  try {
    items = JSON.parse(data.textContent);
  } catch (err) {
    dbg('gallery: bad items', err);
    return;
  }
  const image = gallery.querySelector('[data-gallery-image]');
  const link = gallery.querySelector('[data-gallery-link]');
  const counter = gallery.querySelector('[data-gallery-counter]');
  const caption = gallery.querySelector('[data-gallery-caption]');
  const nav = gallery.querySelector('.content-gallery__nav, [data-gallery-nav]');
  const open = gallery.querySelector('[data-gallery-open]');
  const start = Math.min(Math.max(Number(gallery.dataset.galleryStart) || 0, 0), items.length - 1);
  let current = start;

  function show(index) {
    current = (index + items.length) % items.length;
    const item = items[current];
    image.src = item.src;
    image.alt = item.title;
    if (link) link.href = item.file;
    if (counter) counter.textContent = `${current + 1} / ${items.length}`;
    if (caption) {
      caption.textContent = item.title;
      caption.href = item.page;
    }
    if (open) {
      open.href = item.page;
      open.hidden = current === start;
    }
  }

  gallery.querySelector('[data-gallery-previous]')?.addEventListener('click', () => show(current - 1));
  gallery.querySelector('[data-gallery-next]')?.addEventListener('click', () => show(current + 1));
  document.addEventListener('keydown', (event) => {
    // Not while typing (the comment form); target may be the document itself.
    if (closest(event, 'input, textarea, select, [contenteditable]')) return;
    if (event.key === 'ArrowLeft') show(current - 1);
    if (event.key === 'ArrowRight') show(current + 1);
  });
  document.querySelectorAll('[data-gallery-show]').forEach((el) => {
    el.addEventListener('click', (event) => {
      event.preventDefault();
      show(Number(el.dataset.galleryShow));
      gallery.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
  if (nav) nav.hidden = false;
}

export function bindGalleries(root) {
  root.querySelectorAll(SELECTOR).forEach((gallery) => bindGallery(gallery));
}
