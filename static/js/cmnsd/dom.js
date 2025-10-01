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

/**
 * Convert arbitrary payload into an array of Nodes,
 * preserving document order per input.
 */
export function toNodes(payload) {
  if (payload == null) return [];
  if (payload instanceof DocumentFragment) return Array.from(payload.childNodes);
  if (payload instanceof Node) return [payload];
  if (Array.isArray(payload)) {
    const nodes = [];
    payload.forEach(item => {
      if (item instanceof Node) nodes.push(item);
      else nodes.push(...toNodes(htmlToFragment(String(item))));
    });
    return nodes;
  }
  // string or other → treat as HTML
  return Array.from(htmlToFragment(String(payload)).childNodes);
}

export function normalizePayload(payload) {
  // Kept for backwards-compat where callers want a Fragment
  const frag = document.createDocumentFragment();
  toNodes(payload).forEach(n => frag.appendChild(n));
  return frag;
}

/**
 * Append content to a container (append mode).
 * @deprecated Prefer insert(container, payload, { position: 'bottom'|'top' })
 */
export function inject(container, payload) {
  const el = resolveContainer(container);
  el.appendChild(normalizePayload(payload));
  return el;
}

/**
 * Replace the content of a container.
 * Fires cmnsd:content:applied on the container afterwards.
 */
export function update(container, payload) {
  const el = resolveContainer(container);
  el.replaceChildren();
  el.appendChild(normalizePayload(payload));

  // const ev = new CustomEvent('cmnsd:content:applied', { bubbles: true });
  // el.dispatchEvent(ev);
  const ev = new CustomEvent('cmnsd:content:applied', {
    bubbles: true,
    detail: { container: el }
  });
  el.dispatchEvent(ev);

  return el;
}

/**
 * Insert nodes at the top or bottom of the container.
 * If any inserted element has an id that already exists
 * within the container, the existing element is replaced in place.
 * Fires cmnsd:content:applied on the container afterwards.
 *
 * @param {string|Element} container
 * @param {any} payload - string | Node | Node[] | DocumentFragment
 * @param {{ position?: 'top' | 'bottom' }} [options]
 */
export function insert(container, payload, options = {}) {
  const el = resolveContainer(container);
  const position = options.position === 'top' ? 'top' : 'bottom';

  const nodes = toNodes(payload);
  const iterable = position === 'top' ? [...nodes].reverse() : nodes;

  iterable.forEach(node => {
    if (node.nodeType === Node.ELEMENT_NODE) {
      const id = /** @type {HTMLElement} */ (node).id;
      if (id) {
        const existing = el.querySelector(`#${CSS.escape(id)}`);
        if (existing && el.contains(existing)) {
          existing.replaceWith(node);
          return;
        }
      }
    }

    if (position === 'top') el.insertBefore(node, el.firstChild);
    else el.appendChild(node);
  });

  const ev = new CustomEvent('cmnsd:content:applied', { bubbles: true });
  el.dispatchEvent(ev);

  return el;
}

/**
 * Delegated event binding.
 */
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
