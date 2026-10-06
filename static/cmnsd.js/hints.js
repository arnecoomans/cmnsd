// Hints while filling in a form, for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// An element inside a form, marked
//   data-cmnsd-hint="<address>"  data-cmnsd-hint-fields="given_name last_name"
// is filled with what that address answers (the cmnsd response shape:
// `html`) for the form's current values of those fields - asked while
// typing in them (debounced; a request still in flight is aborted, only
// the latest counts) and once on load when they already hold something.
// For advice that doesn't block anything - e.g. "already in the archive?"
// under the names of a new person. The form itself is untouched: it
// submits as it would without this.

import { latest, request } from './api.js';
import { once } from './dom.js';
import { enhance } from './enhance.js';
import { dbg } from './context.js';

const SELECTOR = '[data-cmnsd-hint]';
const DELAY = 300;

function bindHint(hint) {
  if (!once(hint, 'hint')) return;
  const form = hint.closest('form');
  if (!form) return;
  const names = (hint.dataset.cmnsdHintFields || '').split(/\s+/).filter(Boolean);
  const fields = names.map((name) => form.elements.namedItem(name)).filter(Boolean);
  if (!fields.length) return;

  const run = latest(async (signal) => {
    const url = new URL(hint.dataset.cmnsdHint, window.location.href);
    fields.forEach((field) => { if (field.value.trim()) url.searchParams.set(field.name, field.value.trim()); });
    try {
      const { data } = await request(url.toString(), { signal, messages: 'none' });
      hint.innerHTML = data.html || '';
      enhance(hint);
    } catch (err) {
      if (err.name !== 'AbortError') dbg('hint failed', url.toString(), err);
    }
  }, DELAY);

  fields.forEach((field) => field.addEventListener('input', () => run()));
  if (fields.some((field) => field.value.trim())) run.now();
}

export function bindHints(root) {
  root.querySelectorAll(SELECTOR).forEach((hint) => bindHint(hint));
}
