// Single-choice toggle buttons for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// A group marked data-cmnsd-toggle-single holds checkboxes (styled as
// buttons by the project): pressing one releases the others, pressing it
// again releases it too - so "at most one", with none meaning "not set"
// (unlike radios, which can't be released). The server checks the same.
// Event delegation: groups in forms that appear later (a dialog's form)
// work without binding.

import { closest } from './dom.js';

export function bindToggles(root) {
  root.addEventListener('change', (event) => {
    const box = event.target;
    if (!box.matches || !box.matches('input[type=checkbox]') || !box.checked) return;
    const group = closest(event, '[data-cmnsd-toggle-single]');
    if (!group) return;
    group.querySelectorAll('input[type=checkbox]').forEach((other) => {
      if (other !== box) other.checked = false;
    });
  });
}
