// API actions for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// A form or button marked data-cmnsd-action="<action>" with data-model +
// data-object-token POSTs to <apiRoot><model>/<token>/<action>/ (an
// @api_action, cmnsd/views/api/object_action.py) and puts the returned
// `html` in place:
//
//   data-cmnsd-target  where: a CSS selector, or "closest:<selector>"
//                      (an ancestor of the form/button itself)
//   data-cmnsd-insert  how: append | prepend | replace | remove
//   data-cmnsd-confirm optional question to confirm first
//
// A form sends its fields (as JSON); a button sends nothing. Errors go
// into the form's [data-cmnsd-error] element, or an alert. Event
// delegation: elements added later (a new comment's own buttons) work
// without rebinding.

import { csrfToken } from './csrf.js';

function resolveTarget(el) {
  const spec = el.dataset.cmnsdTarget || '';
  if (spec.startsWith('closest:')) return el.closest(spec.slice('closest:'.length));
  return spec ? document.querySelector(spec) : null;
}

function showError(el, message) {
  const slot = el.querySelector('[data-cmnsd-error]');
  if (slot) {
    slot.textContent = message;
    slot.hidden = false;
  } else {
    window.alert(message);
  }
}

function place(el, html) {
  const target = resolveTarget(el);
  if (!target) return;
  const mode = el.dataset.cmnsdInsert || 'replace';
  if (mode === 'remove' || (mode === 'replace' && !html)) {
    target.remove();
  } else if (mode === 'replace') {
    target.outerHTML = html;
  } else if (html) {
    target.insertAdjacentHTML(mode === 'prepend' ? 'afterbegin' : 'beforeend', html);
  }
}

async function run(el, data, config, dbg) {
  const { cmnsdAction: action, model, objectToken: token, cmnsdConfirm: question } = el.dataset;
  if (question && !window.confirm(question)) return;
  const url = `${config.apiRoot}${encodeURIComponent(model)}/${encodeURIComponent(token)}/${encodeURIComponent(action)}/`;
  const controls = el.matches('form') ? el.querySelectorAll('button, textarea, input') : [el];
  controls.forEach((c) => { c.disabled = true; });
  const slot = el.querySelector && el.querySelector('[data-cmnsd-error]');
  if (slot) slot.hidden = true;
  dbg('POST', url, data);
  try {
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken(), 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify(data),
    });
    const result = await res.json().catch(() => ({ ok: false, error: `HTTP ${res.status}` }));
    if (!res.ok || !result.ok) {
      showError(el, result.error || `HTTP ${res.status}`);
      return;
    }
    place(el, result.html);
    if (el.matches('form') && el.isConnected) el.reset();
  } catch (err) {
    dbg('action failed', url, err);
    showError(el, err.message);
  } finally {
    controls.forEach((c) => { c.disabled = false; });
  }
}

export function bindActions(root, config, dbg) {
  root.addEventListener('submit', (event) => {
    const form = event.target.closest('form[data-cmnsd-action]');
    if (!form) return;
    event.preventDefault();
    run(form, Object.fromEntries(new FormData(form)), config, dbg);
  });
  root.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-cmnsd-action]');
    if (!button) return;
    event.preventDefault();
    run(button, {}, config, dbg);
  });
}
