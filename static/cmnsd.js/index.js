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
import { bindMenus } from './menus.js';
import { bindPickers } from './picker.js';
import { bindMessages, showMessage } from './messages.js';
import { bindEditBlocks } from './edit.js';
import { bindSuggestions } from './suggest.js';
import { enhance, registerEnhancer } from './enhance.js';
import { bindViewers } from './viewer.js';
import { bindAutosaves } from './autosave.js';
import { bindToggles } from './toggles.js';
import { bindCreateButtons } from './dialog.js';
import { bindUploads } from './upload.js';
import { bindHints } from './hints.js';
import { bindLightboxes } from './lightbox.js';
import { bindVia } from './via.js';
import { config, configure, dbg } from './context.js';

function whenReady(fn) {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fn, { once: true });
  } else {
    fn();
  }
}

// init({apiRoot, sectionStateUrl, sortStateUrl, debug}) - the settings go
// to context.js, where every module reads them.
export function init(settings = {}) {
  configure(settings);
  dbg('init', config);
  // Per element (enhance.js): run on the document now, and by every module
  // on the HTML it puts on the page. Idempotent - safe to run again.
  registerEnhancer(bindLists);
  registerEnhancer(bindFilters);
  registerEnhancer(bindSorts);
  registerEnhancer(bindSections);
  registerEnhancer(bindGalleries);
  registerEnhancer(bindPickers);
  registerEnhancer(bindViewers);
  registerEnhancer(bindAutosaves);
  registerEnhancer(bindUploads);
  registerEnhancer(bindHints);
  registerEnhancer(bindVia);
  registerEnhancer(loadFields);
  whenReady(() => {
    // Delegated, once on the document: they work for HTML added later.
    bindMessages(document);
    bindActions(document);
    bindMenus(document);
    bindEditBlocks(document);
    bindLightboxes(document);
    bindSuggestions(document);
    bindToggles(document);
    bindCreateButtons(document);
    enhance(document);
  });
}

// Enhance HTML a project script put on the page (enhance.js): its
// deferred fields, pills, pickers, ... - load() is the older name.
export { enhance };
export function load(root = document) {
  enhance(root);
}

// Show a message in the message area (messages.js), e.g. from a project
// script: cmnsd.message('Saved', 'success'). Levels: success, info,
// warning, error, debug.
export function message(text, level = 'info') {
  showMessage(text, level);
}

export default { init, enhance, load, message };
