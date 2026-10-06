// Suggestions for free-text fields for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// An input marked data-cmnsd-suggest="<url>" with a list="<datalist id>"
// (cmnsd.forms.widgets.SuggestInput): typing (debounced) GETs
// <url>?q=<text> (cmnsd object_suggest - existing values of that field,
// most used first) and fills the <datalist>, so the browser shows them as
// it does its own suggestions. Choosing one only fills in the text.
// Event delegation: inputs in forms that appear later (an edit-mode
// block's form) work without binding.

import { latest, request } from './api.js';
import { closest } from './dom.js';
import { dbg } from './context.js';

const DELAY = 200;
const searches = new WeakMap();   // input -> its latest() search

function searchFor(input) {
  if (!searches.has(input)) {
    searches.set(input, latest(async (signal) => {
      const list = input.list;
      const query = input.value.trim();
      if (!list) return;
      if (!query) {
        list.innerHTML = '';
        return;
      }
      const url = `${input.dataset.cmnsdSuggest}?${new URLSearchParams({ q: query })}`;
      try {
        const { data } = await request(url, { signal });
        list.replaceChildren(...(data.values || []).map((value) => {
          const option = document.createElement('option');
          option.value = value;
          return option;
        }));
      } catch (err) {
        if (err.name !== 'AbortError') dbg('suggest failed', url, err);
      }
    }, DELAY));
  }
  return searches.get(input);
}

export function bindSuggestions(root) {
  root.addEventListener('input', (event) => {
    const input = closest(event, 'input[data-cmnsd-suggest]');
    if (input) searchFor(input)();
  });
}
