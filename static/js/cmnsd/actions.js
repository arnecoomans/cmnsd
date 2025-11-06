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

    // 🧩 INFO BOX HANDLER (local or remote)
    if (el.dataset.action === 'info') {
      const title = el.dataset.title || 'Info';
      const placement = el.dataset.placement || 'bottom';
      const width = el.dataset.width || '400px';
      const localHTML = el.dataset.info;

      async function showBox(html) {
        document.querySelectorAll('.cmnsd-infobox').forEach(b => b.remove());

        const box = document.createElement('div');
        box.className = 'cmnsd-infobox shadow rounded border bg-white p-3';
        box.style.position = 'absolute';
        box.style.zIndex = '3050';
        box.style.maxWidth = width;
        box.style.pointerEvents = 'auto';
        box.innerHTML = `
          <div class="d-flex justify-content-between align-items-start mb-2">
            <h6 class="fw-bold me-2 mb-0">${title}</h6>
            <button type="button" class="btn-close btn-sm" aria-label="Close"></button>
          </div>
          <div class="cmnsd-infobox-body">${html}</div>
        `;
        document.body.appendChild(box);

        const rect = el.getBoundingClientRect();
        const margin = 6;
        let top, left;

        box.style.top = '-9999px';
        box.style.left = '-9999px';
        const boxRect = box.getBoundingClientRect();

        switch (placement) {
          case 'top':
            top = rect.top + window.scrollY - boxRect.height - margin;
            left = rect.left + window.scrollX;
            break;
          case 'right':
            top = rect.top + window.scrollY;
            left = rect.right + window.scrollX + margin;
            break;
          case 'left':
            top = rect.top + window.scrollY;
            left = rect.left + window.scrollX - boxRect.width - margin;
            break;
          default:
            top = rect.bottom + window.scrollY + margin;
            left = rect.left + window.scrollX;
        }

        box.style.top = `${top}px`;
        box.style.left = `${left}px`;
        box.style.animation = 'fadeIn 0.2s ease-out';

        const closeBox = () => {
          box.remove();
          document.removeEventListener('click', onClickOutside);
        };
        const onClickOutside = (ev) => {
          if (!box.contains(ev.target) && ev.target !== el) closeBox();
        };
        box.querySelector('.btn-close').addEventListener('click', closeBox);
        document.addEventListener('click', onClickOutside);
      }

      if (localHTML) {
        await showBox(localHTML);
      } else if (el.dataset.url) {
        try {
          const res = await request('GET', el.dataset.url);
          const html = res?.payload?.info || res?.payload || '(no info available)';
          await showBox(html);
        } catch (err) {
          renderMessages(
            [{ level: 'danger', text: 'Failed to load info box.' }],
            getConfig().messages
          );
        }
      } else {
        renderMessages(
          [{ level: 'warning', text: 'No info source provided.' }],
          getConfig().messages
        );
      }
      return;
    }

    // 🧩 COPY TO CLIPBOARD HANDLER
    if (el.dataset.action === 'copy') {
      const text =
        el.dataset.text ||
        (el.dataset.clipboardTarget
          ? document.querySelector(el.dataset.clipboardTarget)?.innerText || ''
          : '');
      if (!text) {
        renderMessages([{ level: 'warning', text: 'Nothing to copy.' }], getConfig().messages);
        return;
      }

      try {
        await navigator.clipboard.writeText(text);
        renderMessages([{ level: 'success', text: 'Copied to clipboard.' }], getConfig().messages);
      } catch (err) {
        renderMessages([{ level: 'danger', text: 'Failed to copy text.' }], getConfig().messages);
      }
      return;
    }

    // 🧩 STANDARD AJAX ACTION HANDLER
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
    let body;
    const bodySpec = el.dataset.body;

    if (bodySpec === 'form') {
      const form = el.closest('form') || (el.tagName.toLowerCase() === 'form' ? el : null);
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
        const rMode = el.dataset.refreshMode === 'insert' ? 'insert' : 'update';
        if (rMap && typeof rMap === 'object') {
          await loadContent({ url: rUrl, params: rParams, map: rMap, mode: rMode });
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

    base.addEventListener('click', (e) => {
      const t = e.target.closest('[data-action]');
      if (!t || !base.contains(t)) return;
      if (t.tagName.toLowerCase() === 'form') return;
      handleActionTrigger(e, t);
    });

    base.addEventListener('submit', (e) => {
      const form = e.target.closest('form[data-action]');
      if (!form || !base.contains(form)) return;
      if (!form.dataset.body || form.dataset.body === '') {
        form.dataset.body = 'form';
      } else {
        console.debug('[cmnsd] using custom data-body for', form);
      }
      handleActionTrigger(e, form);
    });

    dbg('actions:bound', { root: base === document ? 'document' : base });
  };
}