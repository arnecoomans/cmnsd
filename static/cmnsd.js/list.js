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

import { loadFields } from './fields.js';
import { bindFilters } from './filter.js';
import { bindSorts } from './sort.js';

const SELECTOR = 'form[data-cmnsd-list][data-cmnsd-target]';
const DELAY = 250;

function bindForm(form, config, dbg) {
  const target = document.querySelector(form.dataset.cmnsdTarget);
  if (!target) {
    dbg('list target not found', form.dataset.cmnsdTarget);
    return;
  }
  let timer = null;
  let controller = null;

  async function run() {
    // Only the latest request counts - abort one still in flight.
    if (controller) controller.abort();
    controller = new AbortController();

    const params = new URLSearchParams(new FormData(form));
    [...params.keys()].forEach((key) => { if (!params.get(key)) params.delete(key); });
    const query = params.toString();
    const url = `${config.apiRoot}${encodeURIComponent(form.dataset.cmnsdList)}/${query ? `?${query}` : ''}`;
    dbg('GET', url);
    try {
      const res = await fetch(url, {
        credentials: 'same-origin',
        signal: controller.signal,
        headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      });
      const data = await res.json();
      if (data.html != null) {
        target.innerHTML = data.html;
        // The swapped-in HTML may hold its own deferred placeholders,
        // filter pills and sort switch - bind them (the page-load binding
        // only saw the old ones).
        loadFields(target, config, dbg);
        bindFilters(target, dbg);
        bindSorts(target, config, dbg);
        // Keep other parameters already in the address (e.g. a filter pill's
        // ?kind=), only this form's fields change.
        const url = new URL(window.location.href);
        new FormData(form).forEach((_value, key) => url.searchParams.delete(key));
        params.forEach((value, key) => url.searchParams.set(key, value));
        history.replaceState(history.state, '', url);
      }
      if (data.errors) dbg('errors', data.errors);
    } catch (err) {
      if (err.name !== 'AbortError') dbg('request failed', url, err);
    }
  }

  form.addEventListener('input', () => {
    clearTimeout(timer);
    timer = setTimeout(run, DELAY);
  });
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    clearTimeout(timer);
    run();
  });
}

export function bindLists(root, config, dbg) {
  root.querySelectorAll(SELECTOR).forEach((form) => bindForm(form, config, dbg));
}
