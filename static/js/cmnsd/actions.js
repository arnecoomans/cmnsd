// Generic delegated data-action handler for cmnsd.
// Indentation: 2 spaces. Docs in English.

import { update, insert } from './dom.js';

/**
 * @param {Object} deps
 * @param {(method:string, url:string, opts?:any)=>Promise<any>} deps.request
 * @param {(opts:{url:string, params?:object, map:object, mode?:'update'|'insert'})=>Promise<any>} deps.loadContent
 * @param {(res:any)=>Array<{level:string,text:string}>} deps.normalizeMessages
 * @param {(list:any[], opts?:any)=>void} deps.renderMessages
 * @param {Function} deps.dbg
 * @param {() => any} deps.getConfig
 */
export function createActionBinder({
  request,
  loadContent,
  normalizeMessages,
  renderMessages,
  dbg,
  getConfig
}) {
  function safeJSON(s) {
    if (!s) return null;
    try {
      return JSON.parse(s);
    } catch (err) {
      console.warn('[cmnsd:json] invalid JSON', { val: s, err });
      return null;
    }
  }

  function parseParams(val) {
    if (!val) return null;

    if (typeof val === 'string' && val.trim().startsWith('{')) {
      try {
        return JSON.parse(val);
      } catch (err) {
        console.warn('[cmnsd:params] invalid JSON, falling back', { val, err });
      }
    }

    try {
      return Object.fromEntries(new URLSearchParams(val));
    } catch (err) {
      console.warn('[cmnsd:params] invalid querystring', { val, err });
      return null;
    }
  }

  function applyFromExistingPayload(response, map, mode = 'update') {
    const data = response && response.payload ? response.payload : {};
    Object.entries(map || {}).forEach(([key, selector]) => {
      if (!(key in data)) {
        dbg('action:skip (missing key in payload)', { key });
        return;
      }
      const el =
        typeof selector === 'string'
          ? document.querySelector(selector)
          : selector;
      if (!el) {
        dbg('action:skip (no container found)', { key, selector });
        return;
      }

      try {
        if (mode === 'insert') insert(el, data[key]);
        else update(el, data[key]);
        dbg('action:applied', { key, selector, mode });
      } catch (err) {
        dbg('action:apply:error', { key, selector, err });
        throw err;
      }
    });
  }

  async function handleActionTrigger(e, el) {
    e.preventDefault();

    const confirmMsg = el.dataset.confirm;
    if (confirmMsg && !window.confirm(confirmMsg)) return;

    let url =
      el.dataset.url ||
      el.getAttribute('href') ||
      el.getAttribute('action') ||
      (el.form && el.form.action) ||
      '';
    if (!url) {
      dbg('action:missing-url', el);
      return;
    }

    let method = (el.dataset.method || '').toUpperCase();
    if (!method) {
      const tag = el.tagName.toLowerCase();
      method =
        tag === 'a'
          ? 'GET'
          : tag === 'form'
          ? el.getAttribute('method') || 'POST'
          : 'POST';
      method = method.toUpperCase();
    }

    const params = parseParams(el.dataset.params);

    let body = undefined;
    const bodySpec = el.dataset.body;

    // 🧩 Enhanced: support data-body="#form-id"
    if (bodySpec === 'form') {
      const form =
        el.closest('form') || (el.tagName.toLowerCase() === 'form' ? el : null);
      if (form) body = new FormData(form);
    } else if (bodySpec && bodySpec.startsWith('#')) {
      const form = document.querySelector(bodySpec);
      if (form) body = new FormData(form);
    } else if (bodySpec) {
      const parsed = safeJSON(bodySpec);
      body = parsed !== null ? parsed : bodySpec;
    }

    const shouldDisable = el.hasAttribute('data-disable');
    if (shouldDisable) el.disabled = true;

    try {
      dbg('action:request', { method, url, params, hasBody: !!body });
      const res = await request(method, url, { params, data: body });

      const msgs = normalizeMessages(res);
      if (msgs.length) {
        dbg('action:messages', { count: msgs.length });
        renderMessages(msgs, getConfig().messages);
      }

      const mapStr = el.dataset.map;
      if (mapStr) {
        const map = safeJSON(mapStr);
        if (map && typeof map === 'object') {
          const mode = el.dataset.mode === 'insert' ? 'insert' : 'update';
          dbg('action:distribute', { keys: Object.keys(map), mode });
          applyFromExistingPayload(res, map, mode);
        } else {
          dbg('action:map:invalid', mapStr);
        }
      }

      if (el.dataset.refreshUrl) {
        const rUrl = el.dataset.refreshUrl;
        const rParams = parseParams(el.dataset.refreshParams);
        const rMap = safeJSON(el.dataset.refreshMap);
        const rMode =
          el.dataset.refreshMode === 'insert' ? 'insert' : 'update';
        if (rMap && typeof rMap === 'object') {
          await loadContent({
            url: rUrl,
            params: rParams,
            map: rMap,
            mode: rMode
          });
        } else {
          dbg('action:refresh:missing-or-invalid-map', el.dataset.refreshMap);
        }
      }
    } catch (err) {
      const context = url || el.getAttribute('action') || '(unknown)';
      renderMessages(
        [{ level: 'danger', text: `Action failed for ${context}` }],
        getConfig().messages
      );
      dbg('action:error', { error: err, element: el, context });
      const cfg = getConfig();
      cfg.onError && cfg.onError(err);
    } finally {
      if (shouldDisable) el.disabled = false;
    }
  }

  return function bindDelegatedActions(root) {
    const base = root || document;

    // Handle clicks
    base.addEventListener('click', (e) => {
      const t = e.target.closest('[data-action]');
      if (!t || !base.contains(t)) return;

      // ✅ Ignore form tags here — submit listener handles them
      if (t.tagName.toLowerCase() === 'form') return;

      handleActionTrigger(e, t);
    });

    // Handle form submissions
    base.addEventListener('submit', (e) => {
      const form = e.target.closest('form[data-action]');
      if (!form || !base.contains(form)) return;
      if (!form.dataset.body) form.dataset.body = 'form';
      handleActionTrigger(e, form);
    });

    dbg('actions:bound', { root: base === document ? 'document' : base });
  };
}