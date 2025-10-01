// Content loader that distributes response.payload into containers.
// Indentation: 2 spaces. Docs in English.

/**
 * @param {Object} deps
 * @param {(url:string, options?:any)=>Promise<any>} deps.get
 * @param {(container:any, payload:any)=>any} deps.update
 * @param {(container:any, payload:any)=>any} deps.insert
 * @param {(res:any)=>Array<{level:string,text:string}>} deps.normalizeMessages
 * @param {(list:any[], opts?:any)=>void} deps.renderMessages
 * @param {Function} deps.dbg
 * @param {() => any} deps.getConfig
 */
export function createLoader({ get, update, insert, normalizeMessages, renderMessages, dbg, getConfig }) {
  async function loadContent({ url, params, map, mode = 'update', onDone } = {}) {
    if (!url) throw new Error('loadContent: url is required');
    if (!map || typeof map !== 'object') throw new Error('loadContent: map is required');

    dbg('loadContent:start', { url, params, keys: Object.keys(map), mode });
    let response;
    try {
      response = await get(url, { params });
    } catch (err) {
      // Network/parse failure
      renderMessages(
        [{ level: 'danger', text: 'Load failed (network).' }],
        getConfig().messages
      );
      const cfg = getConfig();
      cfg.onError && cfg.onError(err);
      return;
    }

    const data = response && response.payload ? response.payload : {};

    // ✅ Always show messages if present
    const msgs = normalizeMessages(response);
    if (msgs.length) {
      dbg('loadContent:messages', { count: msgs.length });
      renderMessages(msgs, getConfig().messages);
    }

    // ✅ If not ok, show generic error
    if (!response.ok) {
      renderMessages(
        [{ level: 'danger', text: 'Load failed.' }],
        getConfig().messages
      );
    }

    // ✅ Only distribute payload if ok
    if (response.ok) {
      Object.entries(map).forEach(([key, target]) => {
        if (!(key in data)) {
          dbg('loadContent:skip (missing key)', { key });
          return;
        }
        dbg('loadContent:apply', { key, target, mode });
        try {
          mode === 'insert'
            ? insert(target, data[key])
            : update(target, data[key]);
        } catch (err) {
          console.warn('[cmnsd:loadContent] failed to update container', { target, err });
        }
      });
    }

    if (typeof onDone === 'function') onDone({ response });
    dbg('loadContent:done', { url, status: response.status, ok: response.ok });
    return response;
  }

  return { loadContent };
}
