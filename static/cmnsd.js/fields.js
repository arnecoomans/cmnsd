// Deferred field loading for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// Finds elements marked data-load-on-ready="true" that carry
// data-model / data-object-token / data-field, and fills them from
// GET <apiRoot><model>/<token>/<field>/ (cmnsd/views/api/object_fields.py).
// Elements pointing at the same object are batched into one request with
// a comma-separated field list, as the API supports. The API returns
// display-ready content, so a returned value is inserted as-is; no value
// means nothing to do.

const SELECTOR = '[data-load-on-ready="true"][data-model][data-field]';

function groupByObject(elements, dbg) {
  const groups = new Map();
  elements.forEach((el) => {
    const { model, objectToken: token, field } = el.dataset;
    // Token only - see docs/cmnsd_api_design.md #Identification.
    if (!token) {
      dbg('skipped, no data-object-token', el);
      return;
    }
    const key = `${model}/${token}`;
    if (!groups.has(key)) groups.set(key, { model, token, fields: new Map() });
    const fields = groups.get(key).fields;
    if (!fields.has(field)) fields.set(field, []);
    fields.get(field).push(el);
  });
  return groups;
}

async function loadGroup({ model, token, fields }, config, dbg) {
  const names = [...fields.keys()];
  const url = `${config.apiRoot}${encodeURIComponent(model)}/${encodeURIComponent(token)}/${names.map(encodeURIComponent).join(',')}/`;
  dbg('GET', url);
  try {
    const res = await fetch(url, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
    });
    const data = await res.json();
    Object.entries(data.fields || {}).forEach(([name, value]) => {
      if (value == null) return;
      (fields.get(name) || []).forEach((el) => { el.innerHTML = value; });
    });
    if (data.errors) dbg('errors', data.errors);
  } catch (err) {
    dbg('request failed', url, err);
  }
}

export function loadFields(root, config, dbg) {
  const elements = root.querySelectorAll(SELECTOR);
  const groups = groupByObject(elements, dbg);
  return Promise.all([...groups.values()].map((group) => loadGroup(group, config, dbg)));
}
