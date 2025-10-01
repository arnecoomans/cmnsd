// HTTP utilities for cmnsd
// Indentation: 2 spaces. Docs in English.

import { getConfig } from './core.js';

/**
 * Get a cookie by name
 * @param {string} name
 * @returns {string|null}
 */
function getCookie(name) {
  if (!document.cookie) return null;
  const cookies = document.cookie.split(';');
  for (let c of cookies) {
    const [k, v] = c.trim().split('=');
    if (k === name) return decodeURIComponent(v);
  }
  return null;
}

/**
 * Get the current CSRF token (Django default cookie: "csrftoken")
 * @returns {string|null}
 */
function getCsrfToken() {
  return getCookie('csrftoken');
}

// Build querystring from params
export function toQuery(params) {
  if (!params) return '';
  if (typeof params === 'string') return params;
  const usp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null) return;
    if (Array.isArray(v)) v.forEach(val => usp.append(k, val));
    else usp.append(k, v);
  });
  return usp.toString();
}

// Generic request
export async function request(method, url, opts = {}) {
  const cfg = getConfig();
  const { params, data, headers = {}, signal } = opts;

  let finalUrl = url;
  const q = toQuery(params);
  if (q) finalUrl += (finalUrl.includes('?') ? '&' : '?') + q;

  const init = {
    method,
    headers: { ...cfg.headers, ...headers },
    credentials: cfg.credentials || 'same-origin',
    signal
  };

  // Add CSRF if needed
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    if (!(data instanceof FormData)) {
      init.headers['Content-Type'] = 'application/json';
    }
    // ✅ Always fetch CSRF cookie at call time
    const token = getCsrfToken();
    if (token) {
      init.headers['X-CSRFToken'] = token;
    }
  }

  if (data) {
    init.body = data instanceof FormData ? data : JSON.stringify(data);
  }

  if (cfg.beforeRequest) {
    await cfg.beforeRequest({ url: finalUrl, init });
  }

  let res;
  try {
    res = await fetch(finalUrl, init);
  } catch (err) {
    cfg.onError && cfg.onError(err);
    throw err;
  }

  let json;
  try {
    json = await res.json();
  } catch {
    const text = await res.text();
    json = { text };
  }

  if (cfg.afterResponse) {
    await cfg.afterResponse(res);
  }

  // Always return structured result, even on non-200
  return {
    status: res.status,
    ok: res.ok,
    ...json
  };
}

// Shortcut methods
export const api = {
  get: (url, opts) => request('GET', url, opts),
  post: (url, opts) => request('POST', url, opts),
  put: (url, opts) => request('PUT', url, opts),
  patch: (url, opts) => request('PATCH', url, opts),
  delete: (url, opts) => request('DELETE', url, opts)
};
