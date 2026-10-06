// The message area for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// cmnsd/messages.html renders [data-cmnsd-messages] on every page, with
// the Django messages of that page load. This module:
// - shows messages from API responses (`messages`: [{text, level}]) and
//   the client's own (showMessage(text, level), e.g. a failed request);
// - fades success / info / debug after a few seconds; warning and error
//   stay until their close button is used;
// - carries messages over a reload (keepForReload - actions.js uses it
//   for data-cmnsd-insert="reload") through sessionStorage, shown again
//   once the new page is up.

import { closest } from './dom.js';
import { dbg } from './context.js';

const AREA = '[data-cmnsd-messages]';
const KEEP_KEY = 'cmnsd-messages';
const FADE = { success: 4000, info: 5000, debug: 8000 };

function area() {
  return document.querySelector(AREA);
}

function dismiss(el) {
  el.classList.add('is-leaving');
  setTimeout(() => el.remove(), 300);
}

function arm(el) {
  const level = [...el.classList].find((c) => c.startsWith('cmnsd-message--'))?.slice('cmnsd-message--'.length) || 'info';
  if (FADE[level]) setTimeout(() => el.isConnected && dismiss(el), FADE[level]);
}

export function showMessage(text, level = 'info') {
  const container = area();
  if (!container || !text) return;
  const el = document.createElement('div');
  el.className = `cmnsd-message cmnsd-message--${level}`;
  if (level === 'error') el.setAttribute('role', 'alert');
  const span = document.createElement('span');
  span.className = 'cmnsd-message__text';
  span.textContent = text;
  const close = document.createElement('button');
  close.type = 'button';
  close.className = 'cmnsd-message__close';
  close.dataset.cmnsdMessageClose = '';
  close.setAttribute('aria-label', 'Close');
  close.innerHTML = '<i class="bi bi-x-lg"></i>';
  el.append(span, close);
  container.append(el);
  arm(el);
}

export function showMessages(list) {
  (list || []).forEach((message) => showMessage(message.text, message.level));
}

export function keepForReload(list) {
  if (!list || !list.length) return;
  try {
    sessionStorage.setItem(KEEP_KEY, JSON.stringify(list));
  } catch (err) { /* storage unavailable - the messages are simply lost */ }
}

export function bindMessages(root) {
  const container = area();
  if (!container) return;
  container.querySelectorAll('.cmnsd-message').forEach(arm);
  container.addEventListener('click', (event) => {
    const close = closest(event, '[data-cmnsd-message-close]');
    if (close) dismiss(close.closest('.cmnsd-message'));
  });
  try {
    const kept = sessionStorage.getItem(KEEP_KEY);
    if (kept) {
      sessionStorage.removeItem(KEEP_KEY);
      showMessages(JSON.parse(kept));
    }
  } catch (err) { dbg('messages: could not read kept messages', err); }
}

// showError(container, text) - into the container's [data-cmnsd-error]
// (a form's own error line) if it has one, else the message area.
export function showError(container, text) {
  const slot = container?.querySelector?.('[data-cmnsd-error]');
  if (slot) {
    slot.textContent = text;
    slot.hidden = false;
  } else {
    showMessage(text, 'error');
  }
}

// clearError(container) - hides the container's error line again.
export function clearError(container) {
  const slot = container?.querySelector?.('[data-cmnsd-error]');
  if (slot) slot.hidden = true;
}
