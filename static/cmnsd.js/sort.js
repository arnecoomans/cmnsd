// Sort switch for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// A container marked data-cmnsd-sort="<selector>" holds buttons with
// data-sort-key="<key>" and data-sort-direction="asc|desc". Clicking one
// reorders the direct children of <selector> by their data-sort-<key>
// value (compared as text - use sortable values, e.g. ISO dates), marks
// that button active. Items with an empty value always go last, whatever
// the direction; ties keep their current order. The container is rendered
// `hidden` and shown here, so without JS there's no dead switch and the
// server's order stays.
//
// data-cmnsd-sort-save="<key>" on the container: the chosen data-sort-key
// is POSTed as {key, value} to config.sortStateUrl, so the project can
// remember it (cmnsd/ui/state.py) and render that order next time.

import { request } from './api.js';
import { once } from './dom.js';
import { config, dbg } from './context.js';

const SELECTOR = '[data-cmnsd-sort]';

function datasetKey(key) {
  return `sort${key.charAt(0).toUpperCase()}${key.slice(1)}`;
}

function sortItems(target, key, direction) {
  const attr = datasetKey(key);
  const items = [...target.children].map((el, index) => ({ el, index, value: el.dataset[attr] || '' }));
  items.sort((a, b) => {
    if (!a.value || !b.value) return (!a.value) - (!b.value) || a.index - b.index;
    const order = a.value < b.value ? -1 : a.value > b.value ? 1 : 0;
    return (direction === 'desc' ? -order : order) || a.index - b.index;
  });
  items.forEach(({ el }) => target.appendChild(el));
}

function saveChoice(bar, value) {
  const key = bar.dataset.cmnsdSortSave;
  if (!key || !config.sortStateUrl) return;
  request(config.sortStateUrl, { method: 'POST', json: { key, value } })
    .catch((err) => dbg('saving sort failed', err));
}

function bindSort(bar) {
  if (!once(bar, 'sort')) return;
  const target = document.querySelector(bar.dataset.cmnsdSort);
  if (!target) {
    dbg('sort target not found', bar.dataset.cmnsdSort);
    return;
  }
  const buttons = bar.querySelectorAll('[data-sort-key]');
  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      sortItems(target, button.dataset.sortKey, button.dataset.sortDirection || 'asc');
      saveChoice(bar, button.dataset.sortKey);
      buttons.forEach((other) => {
        const active = other === button;
        other.classList.toggle('is-active', active);
        other.setAttribute('aria-pressed', active ? 'true' : 'false');
      });
    });
  });
  bar.hidden = false;
}

export function bindSorts(root) {
  root.querySelectorAll(SELECTOR).forEach((bar) => bindSort(bar));
}
