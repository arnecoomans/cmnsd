// HTTP wrapper with Django-friendly CSRF and JSON handling.
// Indentation: 2 spaces. Docs in English.

export function getCSRFCookie(name = 'csrftoken') {
  if (typeof document === 'undefined') return null;
  const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
  return m ? decodeURIComponent(m[1]) : null;
}

export function toQuery(params = {}) {
  const q = new URLSearchParams();
  Object.entries(params || {}).forEach(([k, v]) => {
    if (v == null) return;
    Array.isArray(v) ? v.forEach(it => q.append(k, it)) : q.append(k, String(v));
  });
  const s = q.toString();
  return s ? `?${s}` : '';
}

/**
 * Create a request function bound to a config getter.
 * Keeps http stateless and testable.
 * @param {() => any} getConfig
 */
export function createRequester(getConfig) {
  return async function request(method, url, { params, data, headers, signal } = {}) {
    const cfg = getConfig();
    const fullURL = new URL((cfg.baseURL || '') + url, window.location.origin);
    if (params) {
      const qs = toQuery(params);
      if (qs) fullURL.search = (fullURL.search ? fullURL.search + '&' : '') + qs.slice(1);
    }

    /** @type {RequestInit} */
    const init = {
      method,
      credentials: cfg.credentials || 'same-origin',
      headers: { 'Accept': 'application/json', ...cfg.headers, ...headers },
      signal
    };

    const unsafe = /^(POST|PUT|PATCH|DELETE)$/i.test(method);
    const token = cfg.csrftoken || getCSRFCookie();
    if (unsafe && token) init.headers['X-CSRFToken'] = token;

    if (data !== undefined) {
      const isFD = (typeof FormData !== 'undefined') && data instanceof FormData;
      if (isFD) init.body = data;
      else if (typeof data === 'string' || data instanceof Blob) init.body = data;
      else { init.headers['Content-Type'] = 'application/json'; init.body = JSON.stringify(data); }
    }

    try {
      if (typeof cfg.beforeRequest === 'function') await cfg.beforeRequest({ url: fullURL.toString(), init });
      if (cfg.debug) console.debug('[cmnsd]', 'request:start', { method, url: fullURL.toString() });

      const res = await fetch(fullURL, init);

      if (typeof cfg.afterResponse === 'function') { try { await cfg.afterResponse(res.clone()); } catch {} }

      const ct = res.headers.get('content-type') || '';
      const payload = ct.includes('application/json') ? await res.json()
                    : ct.includes('text/') ? await res.text()
                    : await res.blob();

      if (cfg.debug) console.debug('[cmnsd]', 'request:end', { status: res.status, ok: res.ok, url: fullURL.toString() });

      if (!res.ok) {
        const err = new Error(`HTTP ${res.status}: ${res.statusText}`);
        err.status = res.status; err.response = res; err.payload = payload;
        cfg.onError && cfg.onError(err);
        throw err;
      }
      return payload;
    } catch (err) {
      if (getConfig().debug) console.debug('[cmnsd]', 'request:error', err);
      const cfg2 = getConfig();
      cfg2.onError && cfg2.onError(err);
      throw err;
    }
  };
}
