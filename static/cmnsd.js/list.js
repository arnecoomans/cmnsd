// Live list filtering for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// Enhances a plain GET form marked data-cmnsd-list="<model>" and
// data-cmnsd-target="<selector>". While typing (debounced) or on submit,
// it sends the form's fields as a query string to
// GET <apiRoot><model>/?... (cmnsd/views/api/object_list.py), puts the
// response's `html` into the target, and updates the page URL so a
// reload or shared link shows the same filtered list. Without JS the
// form still submits normally and the page renders server-side.
//
// data-cmnsd-list-url="<address>" instead of data-cmnsd-list: the same,
// but asking that address (with the query string) - a page that searches
// more than one model (e.g. a site search) and answers its own JSON
// request with the same `html` shape.

import { apiUrl, latest, request } from './api.js';
import { once } from './dom.js';
import { enhance } from './enhance.js';
import { config, dbg } from './context.js';

const SELECTOR = 'form[data-cmnsd-list][data-cmnsd-target], form[data-cmnsd-list-url][data-cmnsd-target]';
const DELAY = 250;

function bindForm(form) {
  if (!once(form, 'list')) return;
  const target = document.querySelector(form.dataset.cmnsdTarget);
  if (!target) {
    dbg('list target not found', form.dataset.cmnsdTarget);
    return;
  }

  // Only the latest search counts (api.js latest: waits DELAY while
  // typing, aborts the request before).
  const run = latest(async (signal) => {
    const params = new URLSearchParams(new FormData(form));
    [...params.keys()].forEach((key) => { if (!params.get(key)) params.delete(key); });
    const own = form.dataset.cmnsdListUrl;
    const url = own
      ? `${own}${params.toString() ? `?${params}` : ''}`
      : apiUrl(config.apiRoot, [form.dataset.cmnsdList], params);
    dbg('GET', url);
    try {
      const { data } = await request(url, { signal });
      if (data.html != null) {
        target.innerHTML = data.html;
        // The new results may hold deferred fields, filter pills, a sort
        // switch, ... - enhance them (enhance.js).
        enhance(target);
        // Keep other parameters already in the address (e.g. a filter pill's
        // ?kind=), only this form's fields change.
        const address = new URL(window.location.href);
        new FormData(form).forEach((_value, key) => address.searchParams.delete(key));
        params.forEach((value, key) => address.searchParams.set(key, value));
        history.replaceState(history.state, '', address);
      }
      if (data.errors) dbg('errors', data.errors);
    } catch (err) {
      if (err.name !== 'AbortError') dbg('request failed', url, err);
    }
  }, DELAY);

  form.addEventListener('input', () => run());
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    run.now();
  });
}

export function bindLists(root) {
  root.querySelectorAll(SELECTOR).forEach((form) => bindForm(form));
}
