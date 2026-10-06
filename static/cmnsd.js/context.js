// Shared settings for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// The configuration init() received (index.js) and the debug logger - one
// place, imported by the modules that need them, instead of being passed
// through every function.

export const config = {
  apiRoot: '/api/',
  // Where sections.js POSTs a section's open/closed state; unset = not saved.
  sectionStateUrl: null,
  // Where sort.js POSTs a remembered sort order; unset = not saved.
  sortStateUrl: null,
  debug: false,
};

export function configure(values = {}) {
  Object.assign(config, values);
}

export function dbg(...args) {
  if (config.debug) console.debug('[cmnsd]', ...args);
}
