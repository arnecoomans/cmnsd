// Generic delegated data-action handler for cmnsd.
// Indentation: 2 spaces. Docs in English.

/**
 * @param {Object} deps
 * @param {(method:string, url:string, opts?:any)=>Promise<any>} deps.request
 * @param {(opts:{url:string, params?:object, map:object, mode?:'update'|'insert'})=>Promise<any>} deps.loadContent
 * @param {(res:any)=>Array<{level:string,text:string}>} deps.normalizeMessages
 * @param {(list:any[], opts?:any)=>void} deps.renderMessages
 * @param {Function} deps.dbg
 * @param {() => any} deps.getConfig
 */
export function createActionBinder({ request, loadContent, normalizeMessages, renderMessages, dbg, getConfig }) {
  function safeJSON(s) {
    if (!s) return null;
    try { return JSON.parse(s); } catch { return null; }
  }
  const parseParams = (val) => {
    if (!val) return null;
    try {
      if (typeof val === 'string' && val.trim().startsWith('{')) return JSON.parse(val);
      return Object.fromEntries(new URLSearchParams(val));
    } catch { return null; }
  };

  async function handleActionTrigger(e, el) {
    e.preventDefault();

    const confirmMsg = el.dataset.confirm;
    if (confirmMsg && !window.confirm(confirmMsg)) return;

    let url = el.dataset.url || el.getAttribute('href') || (el.form && el.form.action) || '';
    if (!url) { dbg('action:missing-url', el); return; }

    let method = (el.dataset.method || '').toUpperCase();
    if (!method) {
      const tag = el.tagName.toLowerCase();
      method = (tag === 'a') ? 'GET' : (tag === 'form' ? (el.getAttribute('method') || 'POST') : 'POST');
      method = method.toUpperCase();
    }

    const params = parseParams(el.dataset.params);

    let body = undefined;
    const bodySpec = el.dataset.body;
    if (bodySpec === 'form') {
      const form = el.closest('form') || (el.tagName.toLowerCase() === 'form' ? el : null);
      if (form) body = new FormData(form);
    } else if (bodySpec) {
      try { body = JSON.parse(bodySpec); } catch { body = bodySpec; }
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
          const mode = (el.dataset.mode === 'insert') ? 'insert' : 'update';
          dbg('action:distribute', { keys: Object.keys(map), mode });
          const data = res && res.payload ? res.payload : {};
          Object.entries(map).forEach(([key, target]) => {
            if (!(key in data)) { dbg('distribute:skip (missing key)', { key }); return; }
            // use loadContent shape by faking a one-off map
            // (loadContent would refetch; we apply directly here instead)
            const container = typeof target === 'string' ? target : target;
            if (mode === 'insert') {
              const evt = new CustomEvent('cmnsd:insert', { detail: { key, container } });
              document.dispatchEvent(evt);
            }
          });
          // Direct DOM update handled by loader in core (we avoid circular dep here)
          // Instead, re-use a tiny inline applier:
          applyFromExistingPayload(res, map, mode);
        } else {
          dbg('action:map:invalid', mapStr);
        }
      }

      if (el.dataset.refreshUrl) {
        const rUrl = el.dataset.refreshUrl;
        const rParams = parseParams(el.dataset.refreshParams);
        const rMap = safeJSON(el.dataset.refreshMap);
        const rMode = (el.dataset.refreshMode === 'insert') ? 'insert' : 'update';
        if (rMap && typeof rMap === 'object') {
          await loadContent({ url: rUrl, params: rParams, map: rMap, mode: rMode });
        } else {
          dbg('action:refresh:missing-or-invalid-map', el.dataset.refreshMap);
        }
      }
    } catch (err) {
      // show generic alert as fallback
      renderMessages([{ level: 'danger', text: 'Action failed.' }], getConfig().messages);
      const cfg = getConfig();
      cfg.onError && cfg.onError(err);
    } finally {
      if (shouldDisable) el.disabled = false;
    }
  }

  function applyFromExistingPayload(response, map, mode = 'update') {
    const data = response && response.payload ? response.payload : {};
    Object.entries(map || {}).forEach(([key, selector]) => {
      if (!(key in data)) return;
      const el = typeof selector === 'string' ? document.querySelector(selector) : selector;
      if (!el) return;
      if (mode === 'insert') el.appendChild(htmlToFragment(String(data[key])));
      else { el.replaceChildren(); el.appendChild(htmlToFragment(String(data[key]))); }
    });
  }

  function htmlToFragment(html) {
    const tpl = document.createElement('template');
    tpl.innerHTML = String(html).trim();
    return tpl.content;
  }

  return function bindDelegatedActions(root) {
    const base = root || document;

    base.addEventListener('click', (e) => {
      const t = e.target.closest('[data-action]');
      if (!t || !base.contains(t)) return;
      handleActionTrigger(e, t);
    });

    base.addEventListener('submit', (e) => {
      const form = e.target.closest('form[data-action]');
      if (!form || !base.contains(form)) return;
      if (!form.dataset.body) form.dataset.body = 'form';
      handleActionTrigger(e, form);
    });

    dbg('actions:bound', { root: base === document ? 'document' : base });
  };
}
