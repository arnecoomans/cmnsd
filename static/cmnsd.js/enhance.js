// Enhancing new HTML for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// Two kinds of binding: delegated (actions, edit blocks, suggestions,
// menus, messages - bound once on the document, so they work for HTML
// added later by themselves) and per element (filters, sorts, sections,
// galleries, pickers, list forms, deferred fields - they must be run on
// new HTML). enhance(root) runs every per-element binder on root - at
// start-up on the document (index.js registers them), and by every module
// that puts new HTML on the page (a live search, a section opened, an
// action's response, a saved block). The binders are idempotent
// (dom.js once()), so enhancing a root that's partly set up already is
// safe. Registered rather than imported here, so no module that calls
// enhance() has to import the others (no import cycles).

const enhancers = [];

export function registerEnhancer(fn) {
  enhancers.push(fn);
}

export function enhance(root = document) {
  if (!root) return;
  enhancers.forEach((fn) => fn(root));
}
