// Modal overlay for cmnsd.
// Binds to [data-action="modal"] elements.
//
// Attributes on trigger element:
//   data-title          Header title text (optional).
//   data-url            Remote URL to load body content from.
//   data-content        Inline HTML for body (skips fetch if set).
//   data-content-key    Key inside response.payload to use as body HTML.
//                       Defaults to 'content', fallback to first key in payload.
//   data-on-close-url   URL to fetch when the modal closes.
//   data-on-close-map   JSON map of payload keys → DOM selectors to update after close.
//                       Requires data-on-close-url.
//                       Example: '{"topactions": "#topactions", "media": "#ordered_media"}'
//                       On close, dispatches cmnsd:modal:closed with { url, map } so
//                       core.js can call loadContent without a circular dependency.
//
// Attributes inside modal body:
//   data-close-modal    Clicking this element closes the modal.
//                       Place on a cancel button or a submit button that should
//                       dismiss on success.
//
// Keyboard: Escape closes the modal.
// Indentation: 2 spaces. Docs in English.

import { api } from './http.js';

const Z = 3500;
let modalEl = null;
let bound = false;
let _onCloseUrl = null;
let _onCloseMap = null;

function injectStyles() {
  if (document.getElementById('cmnsd-modal-styles')) return;
  const s = document.createElement('style');
  s.id = 'cmnsd-modal-styles';
  s.textContent = `
    @keyframes cmnsd-modal-in { from { opacity:0; transform:translateY(-12px) } to { opacity:1; transform:translateY(0) } }
    #cmnsd-modal-dialog { animation: cmnsd-modal-in 0.18s ease; }
    #cmnsd-modal-close:hover { color: #343a40 !important; }
  `;
  document.head.appendChild(s);
}

function buildModal() {
  const backdrop = document.createElement('div');
  backdrop.id = 'cmnsd-modal-backdrop';
  backdrop.style.cssText = `
    position:fixed; inset:0; z-index:${Z};
    background:rgba(0,0,0,0.5);
    display:flex; align-items:center; justify-content:center;
    padding:1rem;
  `;

  const dialog = document.createElement('div');
  dialog.id = 'cmnsd-modal-dialog';
  dialog.style.cssText = `
    background:#fff; border-radius:8px;
    box-shadow:0 8px 32px rgba(0,0,0,0.22);
    max-width:520px; width:100%; max-height:90vh;
    display:flex; flex-direction:column; overflow:hidden;
  `;

  const header = document.createElement('div');
  header.id = 'cmnsd-modal-header';
  header.style.cssText = `
    display:flex; align-items:center; justify-content:space-between;
    padding:1rem 1.25rem; border-bottom:1px solid #dee2e6; flex-shrink:0;
  `;

  const title = document.createElement('h5');
  title.id = 'cmnsd-modal-title';
  title.style.cssText = 'margin:0; font-size:1.1rem; font-weight:600;';

  const closeBtn = document.createElement('button');
  closeBtn.id = 'cmnsd-modal-close';
  closeBtn.innerHTML = '&times;';
  closeBtn.setAttribute('aria-label', 'Close');
  closeBtn.style.cssText = `
    background:none; border:none; font-size:1.5rem; line-height:1;
    cursor:pointer; color:#6c757d; padding:0; margin-left:1rem;
    transition:color 0.15s;
  `;
  closeBtn.addEventListener('click', closeModal);

  header.appendChild(title);
  header.appendChild(closeBtn);

  const body = document.createElement('div');
  body.id = 'cmnsd-modal-body';
  body.style.cssText = 'padding:1.25rem; overflow-y:auto; flex:1;';

  dialog.appendChild(header);
  dialog.appendChild(body);
  backdrop.appendChild(dialog);

  // Click on backdrop (outside dialog) closes
  backdrop.addEventListener('click', e => {
    if (e.target === backdrop) closeModal();
  });

  // Delegate data-close-modal inside the dialog
  dialog.addEventListener('click', e => {
    if (e.target.closest('[data-close-modal]')) closeModal();
  });

  return backdrop;
}

function getModal() {
  if (!modalEl) {
    modalEl = buildModal();
    document.body.appendChild(modalEl);
  }
  return modalEl;
}

function setContent(title, html) {
  const modal = getModal();
  const titleEl = modal.querySelector('#cmnsd-modal-title');
  const body = modal.querySelector('#cmnsd-modal-body');

  if (titleEl) titleEl.textContent = title || '';
  if (body) {
    body.innerHTML = html;
    // Re-initialize cmnsd features (autosuggest, etc.) inside the new content
    body.dispatchEvent(new CustomEvent('cmnsd:content:applied', {
      bubbles: true,
      detail: { container: body }
    }));
  }
}

export function openModal(title, html) {
  injectStyles();
  setContent(title, html);
  const modal = getModal();
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';

  // Focus first focusable element inside modal
  const body = modal.querySelector('#cmnsd-modal-body');
  const focusable = body?.querySelector('input, select, textarea, button, [tabindex]');
  if (focusable) setTimeout(() => focusable.focus(), 50);
}

export function closeModal() {
  if (!modalEl) return;
  modalEl.style.display = 'none';
  const body = modalEl.querySelector('#cmnsd-modal-body');
  if (body) body.innerHTML = '';
  document.body.style.overflow = '';

  if (_onCloseUrl && _onCloseMap) {
    document.dispatchEvent(new CustomEvent('cmnsd:modal:closed', {
      detail: { url: _onCloseUrl, map: _onCloseMap }
    }));
  }
  _onCloseUrl = null;
  _onCloseMap = null;
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && modalEl && modalEl.style.display === 'flex') {
    closeModal();
  }
});

async function handleTrigger(e, el) {
  e.preventDefault();
  const title = el.dataset.title || '';
  const localContent = el.dataset.content;

  // Store on-close refresh config from trigger
  _onCloseUrl = el.dataset.onCloseUrl || null;
  try {
    _onCloseMap = el.dataset.onCloseMap ? JSON.parse(el.dataset.onCloseMap) : null;
  } catch (err) {
    console.warn('[cmnsd:modal] invalid data-on-close-map JSON', el.dataset.onCloseMap);
    _onCloseMap = null;
  }

  if (localContent) {
    openModal(title, localContent);
    return;
  }

  const url = el.dataset.url || el.getAttribute('href') || '';
  if (!url) {
    console.warn('[cmnsd:modal] no url or data-content on trigger', el);
    return;
  }

  const contentKey = el.dataset.contentKey || 'content';

  // Show loading state while fetching
  openModal(title, '<p style="color:#6c757d; margin:0;">Loading…</p>');

  try {
    const res = await api.get(url);

    if (!res.ok) {
      setContent(title, '<p style="color:#dc3545; margin:0;">Failed to load content.</p>');
      return;
    }

    let html = '';
    if (typeof res.payload === 'string') {
      html = res.payload;
    } else if (res.payload && typeof res.payload === 'object') {
      // Use specified key, or fall back to first key in payload
      html = res.payload[contentKey]
        ?? res.payload[Object.keys(res.payload)[0]]
        ?? '';
    }

    setContent(title, html);
  } catch (err) {
    setContent(title, '<p style="color:#dc3545; margin:0;">Failed to load content.</p>');
    console.error('[cmnsd:modal] fetch failed', err);
  }
}

export function initModal() {
  if (bound) return;
  bound = true;
  injectStyles();

  document.addEventListener('click', e => {
    const t = e.target.closest('[data-action="modal"]');
    if (!t) return;
    handleTrigger(e, t);
  });
}

document.addEventListener('DOMContentLoaded', () => initModal());
