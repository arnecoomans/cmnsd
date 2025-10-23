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
  return Array.from(htmlToFragment(String(payload)).childNodes);
}

export function normalizePayload(payload) {
  const frag = document.createDocumentFragment();
  toNodes(payload).forEach(n => frag.appendChild(n));
  return frag;
}

export function inject(container, payload) {
  const el = resolveContainer(container);
  el.appendChild(normalizePayload(payload));
  return el;
}

export function update(container, payload) {
  const el = resolveContainer(container);

  // Step 1: Dispose Bootstrap tooltips in this container
  if (window.bootstrap && bootstrap.Tooltip) {
    const tooltipEls = el.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltipEls.forEach(t => {
      const instance = bootstrap.Tooltip.getInstance(t);
      if (instance) instance.dispose();
    });
  }

  // Step 2: Replace content
  el.replaceChildren();
  el.appendChild(normalizePayload(payload));

  // Step 3: Trigger event for other features
  const ev = new CustomEvent('cmnsd:content:applied', {
    bubbles: true,
    detail: { container: el }
  });
  el.dispatchEvent(ev);

  // Step 4: Re-initialize Bootstrap tooltips (for new content)
  if (window.bootstrap && bootstrap.Tooltip) {
    const newTooltips = el.querySelectorAll('[data-bs-toggle="tooltip"]');
    newTooltips.forEach(t => new bootstrap.Tooltip(t));
  }

  return el;
}

export function insert(container, payload, options = {}) {
  const el = resolveContainer(container);
  const position = options.position === 'top' ? 'top' : 'bottom';

  const nodes = toNodes(payload);
  const iterable = position === 'top' ? [...nodes].reverse() : nodes;

  iterable.forEach(node => {
    if (node.nodeType === Node.ELEMENT_NODE) {
      const id = node.id;
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

  const ev = new CustomEvent('cmnsd:content:applied', {
    bubbles: true,
    detail: { container: el }
  });
  el.dispatchEvent(ev);

  return el;
}

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

/* ---------------------------------------------------------
   Auto-resize for textareas
   Expands height dynamically based on content.
   Triggered on input and when content is injected.
--------------------------------------------------------- */

function autoResizeTextarea(el) {
  if (!el) return;
  el.style.height = 'auto';
  const lineHeight = parseFloat(getComputedStyle(el).lineHeight) || 20;
  el.style.height = (el.scrollHeight + lineHeight) + 'px';
}

export function initAutoResizeTextareas(root = document) {
  const textareas = root.querySelectorAll('textarea[data-autoresize], textarea.auto-resize');
  textareas.forEach(el => {
    // Skip if already initialized
    if (el.dataset.autoresizeActive) return;
    el.dataset.autoresizeActive = '1';

    el.style.overflow = 'hidden';
    el.style.resize = 'none';
    el.style.transition = 'height 0.15s ease';

    // Resize on input
    el.addEventListener('input', () => autoResizeTextarea(el));

    // Initial resize on load
    autoResizeTextarea(el);
  });
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  initAutoResizeTextareas();
});

// Reinitialize on cmnsd content injection
document.addEventListener('cmnsd:content:applied', e => {
  initAutoResizeTextareas(e.detail?.container || document);
});
