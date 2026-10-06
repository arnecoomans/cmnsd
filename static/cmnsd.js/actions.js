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
//   data-cmnsd-insert  how: append | prepend | replace | remove | reload
//                      (reload: the page, for a change that affects more
//                      than one place - e.g. reordering parts)
//   data-cmnsd-confirm optional question to confirm first
//
// Messages: the response's `messages` (e.g. "Tag added") go to the message
// area (messages.js) - kept over the reload for insert="reload". An error
// goes into the form's [data-cmnsd-error] if it has one, else the message area.
//
// A form sends its fields (as JSON); a button sends its own name=value
// if it has a name (<button name="direction" value="earlier">), else
// nothing. Event delegation: elements added later (a new comment's own
// buttons) work without rebinding; the HTML an action puts on the page is
// enhanced (enhance.js) - its pickers, pills, ... work too.
//
// Counters: after every successful action, each element marked
// data-cmnsd-count="<list selector>" data-cmnsd-count-items="<item selector>"
// shows how many items that list now holds (a comment added or deleted).
// A list that isn't on the page (a folded section never loaded) leaves its
// counter alone - the server's number stays.

import { apiUrl, request } from './api.js';
import { busy, closest, confirmed } from './dom.js';
import { enhance } from './enhance.js';
import { clearError, keepForReload, showError, showMessages } from './messages.js';
import { config, dbg } from './context.js';

function resolveTarget(el) {
  const spec = el.dataset.cmnsdTarget || '';
  if (spec.startsWith('closest:')) return el.closest(spec.slice('closest:'.length));
  return spec ? document.querySelector(spec) : null;
}

function recount() {
  document.querySelectorAll('[data-cmnsd-count]').forEach((counter) => {
    const list = document.querySelector(counter.dataset.cmnsdCount);
    if (!list) return;
    counter.textContent = list.querySelectorAll(counter.dataset.cmnsdCountItems || ':scope > *').length;
  });
}

function place(el, html) {
  const mode = el.dataset.cmnsdInsert || 'replace';
  if (mode === 'reload') {
    // the caller already kept the messages for after the reload
    window.location.reload();
    return;
  }
  const target = resolveTarget(el);
  if (!target) return;
  const parent = target.parentElement;
  if (mode === 'remove' || (mode === 'replace' && !html)) {
    target.remove();
  } else if (mode === 'replace') {
    target.outerHTML = html;
    enhance(parent);
  } else if (html) {
    target.insertAdjacentHTML(mode === 'prepend' ? 'afterbegin' : 'beforeend', html);
    enhance(target);
  }
}

async function run(el, data) {
  if (!confirmed(el)) return;
  const { cmnsdAction: action, model, objectToken: token } = el.dataset;
  const url = apiUrl(config.apiRoot, [model, token, action]);
  const controls = el.matches('form') ? el.querySelectorAll('button, textarea, input') : [el];
  clearError(el);
  dbg('POST', url, data);
  try {
    await busy(controls, async () => {
      // messages: 'none' - shown now, or kept over a reload, decided below.
      const { ok, data: result } = await request(url, { method: 'POST', json: data, messages: 'none' });
      if (!ok) {
        showError(el, result.error);
        showMessages(result.messages);
        return;
      }
      if ((el.dataset.cmnsdInsert || '') === 'reload') keepForReload(result.messages);
      else showMessages(result.messages);
      place(el, result.html);
      recount();
      if (el.matches('form') && el.isConnected) el.reset();
    });
  } catch (err) {
    dbg('action failed', url, err);
    showError(el, err.message);
  }
}

export function bindActions(root) {
  root.addEventListener('submit', (event) => {
    const form = closest(event, 'form[data-cmnsd-action]');
    if (!form) return;
    event.preventDefault();
    run(form, Object.fromEntries(new FormData(form)));
  });
  root.addEventListener('click', (event) => {
    const button = closest(event, 'button[data-cmnsd-action]');
    if (!button) return;
    event.preventDefault();
    run(button, button.name ? { [button.name]: button.value } : {});
  });
}
