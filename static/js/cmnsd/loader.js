// Content loader that distributes response.payload into containers.
// Indentation: 2 spaces. Docs in English.

/**
 * @param {Object} deps
 * @param {(url:string, options?:any)=>Promise<any>} deps.get
 * @param {(container:any, payload:any)=>any} deps.update
 * @param {(container:any, payload:any, opts?:{position?:'top'|'bottom'})=>any} deps.insert
 * @param {(res:any)=>Array<{level:string,text:string}>} deps.normalizeMessages
 * @param {(list:any[], opts?:any)=>void} deps.renderMessages
 * @param {Function} deps.dbg
 */
export function createLoader({ get, update, insert, normalizeMessages, renderMessages, dbg }) {
  async function loadContent({ url, params, map, mode = 'update', onDone } = {}) {
    if (!url) throw new Error('loadContent: url is required');
    if (!map || typeof map !== 'object') throw new Error('loadContent: map is required');

    dbg('loadContent:start', { url, params, keys: Object.keys(map), mode });
    const response = await get(url, { params });
    const data = response && response.payload ? response.payload : {};

    Object.entries(map).forEach(([key, target]) => {
      if (!(key in data)) {
        dbg('loadContent:skip (missing key)', { key });
        return;
      }

      try {
        dbg('loadContent:apply', { key, target, mode });
        if (mode === 'insert') {
          insert(target, data[key], { position: 'bottom' });
        } else {
          update(target, data[key]);
        }
      } catch (err) {
        console.warn('[cmnsd] loadContent: could not render target', { key, target, error: err });
        // continue loop, don’t rethrow
      }
    });

    const msgs = normalizeMessages(response);
    if (msgs.length) {
      dbg('loadContent:messages', { count: msgs.length });
      renderMessages(msgs);
    }

    if (typeof onDone === 'function') onDone({ response });
    dbg('loadContent:done', { url });
    return response;
  }

  return { loadContent };
}