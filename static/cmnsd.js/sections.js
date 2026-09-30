// Collapsible page sections for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// Enhances <details data-cmnsd-section="<key>">:
// - on toggle, POSTs {key, open} to config.sectionStateUrl, so the project
//   can remember the choice (fmly: core/ui_state.py). Where and whether it
//   is stored is the project's business - without sectionStateUrl nothing
//   is saved and sections simply open/close;
// - when opened with a body marked data-load-on-open, fills it through
//   the API like a deferred field (fields.js), then binds any filter pills
//   and sort switches in it. A closed section's body is never rendered server-side.
// Open/close itself is native <details> - it works without JS.

import { loadFields } from './fields.js';
import { bindFilters } from './filter.js';
import { bindSorts } from './sort.js';
import { csrfToken } from './csrf.js';

const SELECTOR = 'details[data-cmnsd-section]';

function saveState(details, config, dbg) {
  if (!config.sectionStateUrl) return;
  const body = JSON.stringify({ key: details.dataset.cmnsdSection, open: details.open });
  fetch(config.sectionStateUrl, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken(), 'X-Requested-With': 'XMLHttpRequest' },
    body,
  }).catch((err) => dbg('saving section state failed', err));
}

async function loadBody(details, config, dbg) {
  const body = details.querySelector('[data-load-on-open="true"]');
  if (!body) return;
  body.dataset.loadOnOpen = 'loading';
  // fields.js picks up [data-load-on-ready="true"] - reuse it for this one.
  body.dataset.loadOnReady = 'true';
  await loadFields(details, config, dbg);
  body.dataset.loadOnOpen = 'done';
  bindFilters(body, dbg);
  bindSorts(body, config, dbg);
}

export function bindSections(root, config, dbg) {
  root.querySelectorAll(SELECTOR).forEach((details) => {
    details.addEventListener('toggle', () => {
      saveState(details, config, dbg);
      if (details.open) loadBody(details, config, dbg);
    });
  });
}
