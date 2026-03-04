// Lightbox overlay for cmnsd.
// Binds to [data-action="lightbox"] elements.
//
// Attributes:
//   data-src          Full-size image URL. Fallback: href, then first <img> src inside element.
//   data-gallery      Group name. All elements sharing a name get arrow navigation.
//   data-caption      Caption text. Fallback: alt of first <img> inside element.
//
// Keyboard: Escape=close, ArrowLeft/ArrowRight=navigate gallery.
// Indentation: 2 spaces. Docs in English.

const Z = 4000;
let current = null; // { items: [{src, caption}], index }

function injectStyles() {
  if (document.getElementById('cmnsd-lightbox-styles')) return;
  const s = document.createElement('style');
  s.id = 'cmnsd-lightbox-styles';
  s.textContent = `
    @keyframes cmnsd-fadein { from { opacity: 0 } to { opacity: 1 } }
    #cmnsd-lightbox { animation: cmnsd-fadein 0.2s ease; }
    #cmnsd-lightbox-prev:hover,
    #cmnsd-lightbox-next:hover { background: rgba(255,255,255,0.25) !important; }
    #cmnsd-lightbox-close:hover { opacity: 1 !important; }
  `;
  document.head.appendChild(s);
}

function buildOverlay() {
  const overlay = document.createElement('div');
  overlay.id = 'cmnsd-lightbox';
  overlay.style.cssText = `
    position:fixed; inset:0; z-index:${Z};
    background:rgba(0,0,0,0.92);
    display:flex; align-items:center; justify-content:center; flex-direction:column;
  `;

  const img = document.createElement('img');
  img.id = 'cmnsd-lightbox-img';
  img.style.cssText = `
    max-width:90vw; max-height:82vh; object-fit:contain;
    border-radius:4px; user-select:none; display:block;
  `;

  const caption = document.createElement('div');
  caption.id = 'cmnsd-lightbox-caption';
  caption.style.cssText = `
    color:rgba(255,255,255,0.75); font-size:0.875rem;
    margin-top:0.75rem; text-align:center; max-width:90vw;
    min-height:1.2em;
  `;

  const closeBtn = document.createElement('button');
  closeBtn.id = 'cmnsd-lightbox-close';
  closeBtn.innerHTML = '&times;';
  closeBtn.setAttribute('aria-label', 'Close');
  closeBtn.style.cssText = `
    position:fixed; top:1rem; right:1.25rem;
    background:none; border:none; color:#fff;
    font-size:2.25rem; line-height:1; cursor:pointer;
    opacity:0.75; z-index:${Z + 1}; padding:0;
  `;
  closeBtn.addEventListener('click', closeLightbox);

  const prevBtn = document.createElement('button');
  prevBtn.id = 'cmnsd-lightbox-prev';
  prevBtn.innerHTML = '&#8249;';
  prevBtn.setAttribute('aria-label', 'Previous');
  prevBtn.style.cssText = `
    position:fixed; left:1rem; top:50%; transform:translateY(-50%);
    background:rgba(255,255,255,0.12); border:none; color:#fff;
    font-size:2.5rem; line-height:1; cursor:pointer;
    border-radius:4px; padding:0.2rem 0.6rem; z-index:${Z + 1};
    transition:background 0.15s;
  `;
  prevBtn.addEventListener('click', e => { e.stopPropagation(); navigate(-1); });

  const nextBtn = document.createElement('button');
  nextBtn.id = 'cmnsd-lightbox-next';
  nextBtn.innerHTML = '&#8250;';
  nextBtn.setAttribute('aria-label', 'Next');
  nextBtn.style.cssText = `
    position:fixed; right:1rem; top:50%; transform:translateY(-50%);
    background:rgba(255,255,255,0.12); border:none; color:#fff;
    font-size:2.5rem; line-height:1; cursor:pointer;
    border-radius:4px; padding:0.2rem 0.6rem; z-index:${Z + 1};
    transition:background 0.15s;
  `;
  nextBtn.addEventListener('click', e => { e.stopPropagation(); navigate(1); });

  const counter = document.createElement('div');
  counter.id = 'cmnsd-lightbox-counter';
  counter.style.cssText = `
    position:fixed; top:1.1rem; left:50%; transform:translateX(-50%);
    color:rgba(255,255,255,0.6); font-size:0.8rem; z-index:${Z + 1};
  `;

  overlay.appendChild(img);
  overlay.appendChild(caption);
  overlay.appendChild(closeBtn);
  overlay.appendChild(prevBtn);
  overlay.appendChild(nextBtn);
  overlay.appendChild(counter);

  overlay.addEventListener('click', e => { if (e.target === overlay) closeLightbox(); });
  return overlay;
}

function getOverlay() {
  let el = document.getElementById('cmnsd-lightbox');
  if (!el) {
    el = buildOverlay();
    document.body.appendChild(el);
  }
  return el;
}

function getGalleryItems(galleryName) {
  return Array.from(
    document.querySelectorAll(`[data-action="lightbox"][data-gallery="${galleryName}"]`)
  ).map(el => itemFromEl(el));
}

function itemFromEl(el) {
  return {
    src: el.dataset.src || el.getAttribute('href') || el.querySelector('img')?.src || '',
    caption: el.dataset.caption || el.querySelector('img')?.getAttribute('alt') || ''
  };
}

function render() {
  if (!current) return;
  const item = current.items[current.index];
  const img = document.getElementById('cmnsd-lightbox-img');
  const caption = document.getElementById('cmnsd-lightbox-caption');
  const prev = document.getElementById('cmnsd-lightbox-prev');
  const next = document.getElementById('cmnsd-lightbox-next');
  const counter = document.getElementById('cmnsd-lightbox-counter');

  if (img) img.src = item.src;
  if (caption) caption.textContent = item.caption || '';

  const multiple = current.items.length > 1;
  if (prev) prev.style.display = multiple ? '' : 'none';
  if (next) next.style.display = multiple ? '' : 'none';
  if (counter) {
    counter.textContent = multiple
      ? `${current.index + 1} / ${current.items.length}`
      : '';
  }
}

function openLightbox(items, index) {
  current = { items, index };
  const overlay = getOverlay();
  overlay.style.display = 'flex';
  document.body.style.overflow = 'hidden';
  render();
}

export function closeLightbox() {
  current = null;
  const overlay = document.getElementById('cmnsd-lightbox');
  if (overlay) overlay.style.display = 'none';
  document.body.style.overflow = '';
}

function navigate(dir) {
  if (!current) return;
  current.index = (current.index + dir + current.items.length) % current.items.length;
  render();
}

document.addEventListener('keydown', e => {
  if (!current) return;
  if (e.key === 'Escape') closeLightbox();
  if (e.key === 'ArrowLeft') navigate(-1);
  if (e.key === 'ArrowRight') navigate(1);
});

export function initLightbox(root = document) {
  injectStyles();
  root.querySelectorAll('[data-action="lightbox"]').forEach(el => {
    if (el.dataset.lightboxActive) return;
    el.dataset.lightboxActive = '1';

    el.addEventListener('click', e => {
      e.preventDefault();
      const galleryName = el.dataset.gallery;
      let items, index;

      if (galleryName) {
        items = getGalleryItems(galleryName);
        index = items.findIndex(it => it.src === itemFromEl(el).src);
        if (index < 0) index = 0;
      } else {
        items = [itemFromEl(el)];
        index = 0;
      }

      openLightbox(items, index);
    });
  });
}

// ---------------------------------------------------------------------------
// Gallery nav — inline prev/next on the page (not in the lightbox overlay).
// Add data-gallery-nav="gallery-name" to the container wrapping the items.
// The container needs position:relative (or Bootstrap's position-relative).
// ---------------------------------------------------------------------------

function buildNavUI(container, galleryName) {
  const nav = document.createElement('div');
  nav.className = 'cmnsd-gallery-nav';
  nav.style.cssText = `
    position:absolute; bottom:0.6rem; right:0.6rem;
    display:flex; align-items:center; gap:0.35rem;
    z-index:10; pointer-events:auto;
  `;

  const btn = (html, label) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.innerHTML = html;
    b.setAttribute('aria-label', label);
    b.style.cssText = `
      background:rgba(0,0,0,0.45); border:none; color:#fff;
      font-size:1.1rem; line-height:1; cursor:pointer;
      border-radius:4px; padding:0.2rem 0.5rem;
      transition:background 0.15s;
    `;
    b.onmouseenter = () => b.style.background = 'rgba(0,0,0,0.7)';
    b.onmouseleave = () => b.style.background = 'rgba(0,0,0,0.45)';
    return b;
  };

  const prevBtn = btn('&#8249;', 'Previous');
  const nextBtn = btn('&#8250;', 'Next');
  const counter = document.createElement('span');
  counter.style.cssText = `
    color:#fff; font-size:0.8rem; background:rgba(0,0,0,0.45);
    padding:0.2rem 0.45rem; border-radius:4px; white-space:nowrap;
  `;

  nav.appendChild(prevBtn);
  nav.appendChild(counter);
  nav.appendChild(nextBtn);
  container.appendChild(nav);

  let navIndex = 0;

  function getItems() {
    return Array.from(
      container.querySelectorAll(`[data-action="lightbox"][data-gallery="${galleryName}"]`)
    );
  }

  function show(index) {
    const items = getItems();
    if (!items.length) return;
    navIndex = (index + items.length) % items.length;

    items.forEach((el, i) => {
      el.style.display = i === navIndex ? '' : 'none';
    });

    const multiple = items.length > 1;
    nav.style.display = multiple ? 'flex' : 'none';
    counter.textContent = `${navIndex + 1} / ${items.length}`;
  }

  prevBtn.addEventListener('click', e => { e.stopPropagation(); show(navIndex - 1); });
  nextBtn.addEventListener('click', e => { e.stopPropagation(); show(navIndex + 1); });

  // Initial render
  show(0);
}

export function initGalleryNav(root = document) {
  root.querySelectorAll('[data-gallery-nav]').forEach(container => {
    if (container.dataset.galleryNavActive) return;
    container.dataset.galleryNavActive = '1';
    buildNavUI(container, container.dataset.galleryNav);
  });
}

document.addEventListener('DOMContentLoaded', () => initLightbox());
document.addEventListener('DOMContentLoaded', () => initGalleryNav());
document.addEventListener('cmnsd:content:applied', e => {
  const root = e.detail?.container || document;
  initLightbox(root);
  initGalleryNav(root);
});
