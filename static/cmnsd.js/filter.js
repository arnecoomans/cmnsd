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
//
// Several containers on one <selector> combine: an element shows when it
// matches each container's choice. data-cmnsd-filter-key="<key>" makes a
// container compare the elements' data-filter-<key> instead (default key:
// value - data-filter-value). data-cmnsd-filter-when="<key>=<value>" makes
// it a second level: shown only while the container with that key has
// that value chosen, and back to "all" when another is chosen - e.g. the
// document types under "Documents":
//   <div data-cmnsd-filter="#grid" data-cmnsd-filter-param="kind">...</div>
//   <div data-cmnsd-filter="#grid" data-cmnsd-filter-key="type"
//        data-cmnsd-filter-when="value=document" data-cmnsd-filter-param="type" hidden>...</div>
// Bind order is page order: a second level comes after its first.
//
// data-cmnsd-filter-save="<key>" on the container (opt-in, unlike the
// address above): a filter that's a preference, not a task - e.g. a
// timeline with or without history. The choice is POSTed as {key, value}
// to config.sortStateUrl, as sort.js does ("all" for ""), so the project
// can remember it (cmnsd/ui/state.py get_sort) and render that button
// .is-active next time.

import { once } from './dom.js';
import { config, dbg } from './context.js';
import { request } from './api.js';

const SELECTOR = '[data-cmnsd-filter]';
const groups = new WeakMap();   // target element -> [bar state], the containers filtering it

// 'value' -> 'filterValue', 'type' -> 'filterType' (dataset names).
function datasetName(key) {
  return `filter${key[0].toUpperCase()}${key.slice(1)}`;
}

function parseWhen(text) {
  if (!text) return null;
  const [key, value = ''] = text.split('=');
  return { key, value };
}

function save(state, value) {
  if (!state.save || !config.sortStateUrl) return;
  request(config.sortStateUrl, { method: 'POST', json: { key: state.save, value: value || 'all' } })
    .catch((err) => dbg('saving filter failed', err));
}

function remember(state, value) {
  if (!state.param) return;
  const url = new URL(window.location.href);
  if (value) url.searchParams.set(state.param, value); else url.searchParams.delete(state.param);
  history.replaceState(history.state, '', url);
}

// Every container on target: open or not (a second level), its buttons'
// state, and which elements show - matching every open choice.
function refresh(target) {
  const bars = groups.get(target) || [];
  const chosen = {};
  bars.forEach((state) => {
    const open = !state.when || chosen[state.when.key] === state.when.value;
    if (!open && state.value) {
      state.value = '';
      remember(state, '');
    }
    if (open || !(state.key in chosen)) chosen[state.key] = state.value;
    state.bar.hidden = !open;
    state.buttons.forEach((button) => {
      const active = button.dataset.filter === state.value;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', active ? 'true' : 'false');
    });
  });
  target.querySelectorAll('[data-filter-value]').forEach((item) => {
    item.hidden = bars.some((state) => state.value && (item.dataset[datasetName(state.key)] || '') !== state.value);
  });
}

function bindFilter(bar) {
  if (!once(bar, 'filter')) return;
  const target = document.querySelector(bar.dataset.cmnsdFilter);
  if (!target) {
    dbg('filter target not found', bar.dataset.cmnsdFilter);
    return;
  }
  const buttons = [...bar.querySelectorAll('[data-filter]')];
  const state = {
    bar,
    buttons,
    key: bar.dataset.cmnsdFilterKey || 'value',
    param: bar.dataset.cmnsdFilterParam,
    save: bar.dataset.cmnsdFilterSave,
    when: parseWhen(bar.dataset.cmnsdFilterWhen),
    value: '',
  };
  groups.set(target, [...(groups.get(target) || []), state]);
  buttons.forEach((button) => button.addEventListener('click', () => {
    state.value = button.dataset.filter;
    remember(state, state.value);
    save(state, state.value);
    refresh(target);
  }));
  const fromUrl = state.param ? new URL(window.location.href).searchParams.get(state.param) : null;
  const initial = (fromUrl && buttons.find((b) => b.dataset.filter === fromUrl))
    || bar.querySelector('[data-filter].is-active');
  state.value = initial ? initial.dataset.filter : '';
  refresh(target);
}

export function bindFilters(root) {
  root.querySelectorAll(SELECTOR).forEach((bar) => bindFilter(bar));
}
