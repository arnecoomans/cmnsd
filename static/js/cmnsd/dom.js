// DOM utilities and operations (inject/update/insert/on).
// Indentation: 2 spaces. Docs in English.

export function resolveContainer(container) {
  if (!container) throw new Error('No container provided.');
  if (typeof container === 'string') {
    const el = document.querySelector(container);
    if (!el) throw new Error(`Container not found: ${container}`);
    return el;
  }
  return container;
}

export function htmlToFragment(html) {
  const tpl = document.createElement('template');
  tpl.innerHTML = String(html).trim();
  return tpl.content;
}

export function normalizePayload(payload) {
  if (payload == null) return document.createDocumentFragment();
  if (payload instanceof Node) return payload;
  if (Array.isArray(payload)) {
    const frag = document.createDocumentFragment();
    payload.forEach(item => frag.appendChild(item instanceof Node ? item : htmlToFragment(String(item))));
    return frag;
  }
  return htmlToFragment(String(payload));
}

export function inject(container, payload) {
  const el = resolveContainer(container);
  el.appendChild(normalizePayload(payload));
  return el;
}

export function update(container, payload) {
  const el = resolveContainer(container);
  el.replaceChildren();
  el.appendChild(normalizePayload(payload));
  return el;
}

// alias requested
export const insert = inject;

export function on(root, type, selector, handler, options) {
  const base = typeof root === 'string' ? document.querySelector(root) : root;
  if (!base) throw new Error('Root element not found for delegation.');
  const wrapped = (e) => {
    const target = e.target.closest(selector);
    if (target && base.contains(target)) handler(e, target);
  };
  base.addEventListener(type, wrapped, options);
  return () => base.removeEventListener(type, wrapped, options);
}
