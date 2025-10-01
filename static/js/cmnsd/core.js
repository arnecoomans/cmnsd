// Core initializer for cmnsd.
// Indentation: 2 spaces. Docs in English.

import { api } from './http.js';
import * as dom from './dom.js';
import * as msg from './messages.js';
import { createActionBinder } from './actions.js';
import { createLoader } from './loader.js';

const state = {
  config: {
    baseURL: '',
    headers: {},
    csrftoken: null,
    credentials: 'same-origin',
    debug: false,
    messages: { container: '#messages', dismissible: true, clearBefore: false, max: 5 },
    actions: { autoBind: true }
  }
};

function dbg(...args) {
  if (state.config.debug) {
    console.debug('[cmnsd]', ...args);
  }
}

const loader = createLoader({
  get: (url, options) => api.get(url, options),
  update: dom.update,
  insert: dom.insert,
  normalizeMessages: msg.normalize,
  renderMessages: (list, opts) =>
    msg.render(list, { ...state.config.messages, ...opts }),
  dbg,
  getConfig: () => state.config
});

const actionBinder = createActionBinder({
  request: api.request || ((m, u, o) => api[m.toLowerCase()](u, o)),
  loadContent: loader.loadContent,
  normalizeMessages: msg.normalize,
  renderMessages: (list, opts) =>
    msg.render(list, { ...state.config.messages, ...opts }),
  dbg,
  getConfig: () => state.config
});

export function init(config = {}) {
  state.config = {
    ...state.config,
    ...config,
    messages: { ...state.config.messages, ...(config.messages || {}) },
    actions: { ...state.config.actions, ...(config.actions || {}) }
  };

  if (state.config.actions.autoBind) {
    actionBinder(document);
  }

  dbg('init', state.config);
}

export function getConfig() {
  return state.config;
}

// ✅ Re-export loadContent at top level
export const loadContent = loader.loadContent;

export { loader, actionBinder, dom, msg, api, dbg };
