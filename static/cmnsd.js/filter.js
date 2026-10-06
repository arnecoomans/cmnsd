// Filter pills for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// A container marked data-cmnsd-filter="<selector>" holds buttons with
// data-filter="<value>" ("" = show all). Clicking one shows only the
// elements inside <selector> whose data-filter-value equals the value,
// and marks that button active (.is-active, aria-pressed). A button
// rendered .is-active with a non-empty value is applied on load - so the
// server can render everything visible (the no-JS fallback) and still
// start on one choice. Purely in the browser - no request. The container is rendered `hidden` and shown
// here, so without JS there are no dead buttons and everything shows.
//
// data-cmnsd-filter-param="<name>" on the container (opt-in): the choice
// goes into the page address as ?<name>=<value> (history.replaceState, no
// reload), and a value already in the address is applied on load - so a
// reload, back/forward or a shared link keep the filter, while a fresh
// visit starts on "all". Not remembered beyond the address on purpose: a
// filter is a task, and a silently remembered one hides things.

import { once } from './dom.js';
import { dbg } from './context.js';

const SELECTOR = '[data-cmnsd-filter]';

function bindFilter(bar) {
  if (!once(bar, 'filter')) return;
  const target = document.querySelector(bar.dataset.cmnsdFilter);
  if (!target) {
    dbg('filter target not found', bar.dataset.cmnsdFilter);
    return;
  }
  const buttons = bar.querySelectorAll('[data-filter]');
  const param = bar.dataset.cmnsdFilterParam;
  const apply = (button) => {
    const value = button.dataset.filter;
    buttons.forEach((other) => {
      const active = other === button;
      other.classList.toggle('is-active', active);
      other.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
    target.querySelectorAll('[data-filter-value]').forEach((item) => {
      item.hidden = Boolean(value) && item.dataset.filterValue !== value;
    });
  };
  const remember = (value) => {
    if (!param) return;
    const url = new URL(window.location.href);
    if (value) url.searchParams.set(param, value); else url.searchParams.delete(param);
    history.replaceState(history.state, '', url);
  };
  buttons.forEach((button) => button.addEventListener('click', () => {
    apply(button);
    remember(button.dataset.filter);
  }));
  const fromUrl = param ? new URL(window.location.href).searchParams.get(param) : null;
  const initial = (fromUrl && [...buttons].find((b) => b.dataset.filter === fromUrl))
    || bar.querySelector('[data-filter].is-active');
  if (initial && initial.dataset.filter) apply(initial);
  bar.hidden = false;
}

export function bindFilters(root) {
  root.querySelectorAll(SELECTOR).forEach((bar) => bindFilter(bar));
}
