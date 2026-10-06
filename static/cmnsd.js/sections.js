// Collapsible page sections for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// Enhances <details data-cmnsd-section="<key>">:
// - on toggle, POSTs {key, open} to config.sectionStateUrl, so the project
//   can remember the choice (cmnsd/ui/state.py, via cmnsd/ui_urls.py) -
//   without sectionStateUrl nothing is saved and sections simply
//   open/close;
// - when opened with a body marked data-load-on-open, fills it through
//   the API like a deferred field (fields.js), then binds any filter pills
//   and sort switches in it. A closed section's body is never rendered server-side.
// Open/close itself is native <details> - it works without JS.

import { loadFields } from './fields.js';
import { request } from './api.js';
import { once } from './dom.js';
import { enhance } from './enhance.js';
import { config, dbg } from './context.js';

const SELECTOR = 'details[data-cmnsd-section]';

function saveState(details) {
  if (!config.sectionStateUrl) return;
  request(config.sectionStateUrl, { method: 'POST', json: { key: details.dataset.cmnsdSection, open: details.open } })
    .catch((err) => dbg('saving section state failed', err));
}

async function loadBody(details) {
  const body = details.querySelector('[data-load-on-open="true"]');
  if (!body) return;
  body.dataset.loadOnOpen = 'loading';
  // fields.js picks up [data-load-on-ready="true"] - reuse it for this one.
  body.dataset.loadOnReady = 'true';
  await loadFields(details);
  body.dataset.loadOnOpen = 'done';
  enhance(body);   // its pills, sort switch, pickers, ... (enhance.js)
}

export function bindSections(root) {
  root.querySelectorAll(SELECTOR).forEach((details) => {
    if (!once(details, 'section')) return;
    details.addEventListener('toggle', () => {
      saveState(details);
      if (details.open) loadBody(details);
    });
  });
}
