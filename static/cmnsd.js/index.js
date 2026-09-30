// Entry point for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// Usage (base.html):
//   <script type="module">
//     import cmnsd from "{% static 'cmnsd.js/index.js' %}";
//     cmnsd.init({ apiRoot: '/api/', debug: true });
//   </script>

import { loadFields } from './fields.js';
import { bindLists } from './list.js';
import { bindFilters } from './filter.js';
import { bindSorts } from './sort.js';
import { bindSections } from './sections.js';
import { bindActions } from './actions.js';
import { bindGalleries } from './gallery.js';

const state = {
  config: {
    apiRoot: '/api/',
    // Where sections.js POSTs a section's open/closed state; unset = not saved.
    sectionStateUrl: null,
    // Where sort.js POSTs a remembered sort order; unset = not saved.
    sortStateUrl: null,
    debug: false,
  },
};

function dbg(...args) {
  if (state.config.debug) console.debug('[cmnsd]', ...args);
}

function whenReady(fn) {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fn, { once: true });
  } else {
    fn();
  }
}

export function init(config = {}) {
  state.config = { ...state.config, ...config };
  dbg('init', state.config);
  whenReady(() => {
    bindLists(document, state.config, dbg);
    bindFilters(document, dbg);
    bindSorts(document, state.config, dbg);
    bindSections(document, state.config, dbg);
    bindActions(document, state.config, dbg);
    bindGalleries(document, dbg);
    loadFields(document, state.config, dbg);
  });
}

// Re-scan a subtree, e.g. after inserting HTML that holds its own
// data-load-on-ready placeholders.
export function load(root = document) {
  return loadFields(root, state.config, dbg);
}

export default { init, load };
