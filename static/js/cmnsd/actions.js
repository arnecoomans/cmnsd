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

  function htmlToFragment(html) {
    const tpl = document.createElement('template');
    tpl.innerHTML = String(html).trim();
    return tpl.content;
  }

  function applyFromExistingPayload(response, map, mode = 'update') {
    const data = response && response.payload ? response.payload : {};
    Object.entries(map || {}).forEach(([key, selector]) => {
      if (!(key in data)) return;
      const el =
        typeof selector === 'string'
          ? document.querySelector(selector)
          : selector;
      if (!el) return;
      const frag = htmlToFragment(String(data[key]));
      if (mode === 'insert') {
        el.appendChild(frag);
      } else {
        el.replaceChildren();
        el.appendChild(frag);
      }
    });
  }

  async function handleActionTrigger(e, el) {
    e.preventDefault();
    e.stopPropagation();

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
    if (bodySpec === 'form') {
      const form =
        el.closest('form') || (el.tagName.toLowerCase() === 'form' ? el : null);
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

      // ✅ Always render server messages if present
      const msgs = normalizeMessages(res);
      if (msgs.length) {
        dbg('action:messages', { count: msgs.length });
        renderMessages(msgs, getConfig().messages);
      }

      // ✅ Add generic error message if request not ok
      if (!res.ok) {
        renderMessages(
          [{ level: 'danger', text: 'Action failed.' }],
          getConfig().messages
        );
      }

      // Apply payload if available
      const mapStr = el.dataset.map;
      if (mapStr && res.ok) {
        const map = safeJSON(mapStr);
        if (map && typeof map === 'object') {
          const mode = el.dataset.mode === 'insert' ? 'insert' : 'update';
          dbg('action:distribute', { keys: Object.keys(map), mode });
          applyFromExistingPayload(res, map, mode);
        } else {
          dbg('action:map:invalid', mapStr);
        }
      }

      // Refresh if requested
      if (el.dataset.refreshUrl && res.ok) {
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
      // Network/parse failure
      renderMessages(
        [{ level: 'danger', text: 'Action failed (network).' }],
        getConfig().messages
      );
      const cfg = getConfig();
      cfg.onError && cfg.onError(err);
    } finally {
      if (shouldDisable) el.disabled = false;
    }
  }

  return function bindDelegatedActions(root) {
    const base = root || document;

    // Click handler (ignore forms)
    base.addEventListener('click', (e) => {
      const t = e.target.closest('[data-action]');
      if (!t || !base.contains(t)) return;
      if (t.tagName.toLowerCase() === 'form') return;
      handleActionTrigger(e, t);
    });

    // Submit handler (for forms)
    base.addEventListener('submit', (e) => {
      const form = e.target.closest('form[data-action]');
      if (!form || !base.contains(form)) return;
      if (!form.dataset.body) form.dataset.body = 'form';
      handleActionTrigger(e, form);
    });

    dbg('actions:bound', { root: base === document ? 'document' : base });
  };
}
