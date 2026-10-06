// The one request client for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// Every module talks to the server through request(): it sends the usual
// headers (JSON, X-Requested-With, the CSRF token on anything but GET),
// reads the cmnsd API response shape (docs/api.md #Response:
// ok, error, errors, messages, plus the endpoint's own keys) - also when
// the server answered with something that isn't JSON (a crash page, a
// proxy error) - and shows the response's `messages` in the message area.
//
//   const { ok, status, data } = await request(url, { method: 'POST', json: {...} });
//
// Options:
//   method     'GET' (default), 'POST', ...
//   json       a body sent as JSON
//   form       a FormData body (a form post; the browser sets the type)
//   signal     an AbortController signal - an abort is rethrown
//              (err.name === 'AbortError'); the caller ignores it
//   messages   'show' (default) - into the message area now;
//              'keep' - kept for after a reload / redirect (messages.js);
//              'none' - left to the caller (data.messages)
//
// Returns { ok, status, data }: ok is false for an HTTP error or data.ok
// false; data always has `ok`, and on an error `error` (a readable
// sentence - "HTTP 500" when the server sent none).

import { csrfToken } from './csrf.js';
import { keepForReload, showMessages } from './messages.js';

export async function request(url, { method = 'GET', json, form, signal, messages = 'show' } = {}) {
  const headers = { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' };
  if (method !== 'GET') headers['X-CSRFToken'] = csrfToken();
  let body;
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(json);
  } else if (form !== undefined) {
    body = form;
  }
  const res = await fetch(url, { method, headers, body, signal, credentials: 'same-origin' });
  let data;
  try {
    data = await res.json();
  } catch (err) {
    data = {};
  }
  if (typeof data !== 'object' || data === null) data = {};
  if (data.ok === undefined) data.ok = res.ok;
  if (!res.ok && !data.error) data.error = `HTTP ${res.status}`;
  if (messages === 'show') showMessages(data.messages);
  else if (messages === 'keep') keepForReload(data.messages);
  return { ok: res.ok && data.ok !== false, status: res.status, data };
}

// apiUrl(apiRoot, [model, token, name], params) - an API address:
// '/api/content/aB3.../form/name/'. Each part URL-encoded, empty parts
// left out, `params` (an object or URLSearchParams) as the query string.
export function apiUrl(apiRoot, parts, params) {
  const path = parts.filter((part) => part !== undefined && part !== null && part !== '')
    .map((part) => encodeURIComponent(part)).join('/');
  const query = params ? new URLSearchParams(params).toString() : '';
  return `${apiRoot}${path}/${query ? `?${query}` : ''}`;
}

// latest(fn, delay) - for "search while typing": calling it (again)
// restarts the wait; when the wait is over, fn(signal, ...args) runs and a
// call still in flight from before is aborted - only the latest counts.
// .now(...args) runs without waiting. An AbortError is swallowed.
export function latest(fn, delay = 0) {
  let timer = null;
  let controller = null;
  const run = async (args) => {
    controller?.abort();
    controller = new AbortController();
    try {
      await fn(controller.signal, ...args);
    } catch (err) {
      if (err.name !== 'AbortError') throw err;
    }
  };
  const call = (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => run(args), delay);
  };
  call.now = (...args) => {
    clearTimeout(timer);
    return run(args);
  };
  call.cancel = () => {
    clearTimeout(timer);
    controller?.abort();
  };
  return call;
}
