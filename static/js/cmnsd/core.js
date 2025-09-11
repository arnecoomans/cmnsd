// Central config, composition, and public API for cmnsd.
// Indentation: 2 spaces. Docs in English.

import { createRequester, toQuery } from './http.js';
import * as dom from './dom.js';
import { normalize as normalizeMessages, render as renderMessages } from './messages.js';
import { createLoader } from './loader.js';
import { createActionBinder } from './actions.js';

const state = {
  config: {
    baseURL: '',
    headers: {},
    csrftoken: null,
    credentials: 'same-origin',
    beforeRequest: null,
    afterResponse: null,
    onError: (e) => console.error('[cmnsd]', e),
    debug: true,
    messages: { container: null, dismissible: true, clearBefore: true },
    actions: { autoBind: true, root: null }
  }
};

function dbg(...args) { if (state.config.debug) console.debug('[cmnsd]', ...args); }
export function getConfig() { return state.config; }
export function setConfig(next) { state.config = { ...state.config, ...next }; }

// HTTP requester bound to current config
const request = createRequester(() => state.config);

// Loader (content distributor) that uses api.get internally
const loader = createLoader({
  get: (url, options) => api.get(url, options),
  update: dom.update,
  insert: dom.insert,
  normalizeMessages,
  renderMessages,
  dbg
});

// Actions binder (generic data-action handler)
const bindActions = createActionBinder({
  request,
  loadContent: loader.loadContent,
  normalizeMessages,
  renderMessages,
  dbg,
  getConfig: () => state.config
});

export const api = {
  init(options = {}) {
    setConfig(options);
    dbg('init', { config: state.config });

    if (state.config.actions?.autoBind) {
      const root = state.config.actions.root || document;
      bindActions(root);
    }
    return this;
  },

  // HTTP
  get(url, options) { return request('GET', url, options); },
  post(url, options) { return request('POST', url, options); },
  put(url, options) { return request('PUT', url, options); },
  patch(url, options) { return request('PATCH', url, options); },
  delete(url, options) { return request('DELETE', url, options); },

  // DOM
  inject: dom.inject,
  insert: dom.insert,
  update: dom.update,
  on: dom.on,

  // Messages
  messages: {
    normalize: normalizeMessages,
    render: (response, opts) => {
      const list = normalizeMessages(response);
      dbg('messages:render', { count: list.length });
      renderMessages(list, { ...state.config.messages, ...opts });
    }
  },

  // Utilities
  util: { toQuery, htmlToFragment: dom.htmlToFragment, resolveContainer: dom.resolveContainer },

  // Content loader
  loadContent: loader.loadContent
};
