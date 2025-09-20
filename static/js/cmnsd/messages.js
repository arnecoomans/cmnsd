// Bootstrap alert helpers (normalize + render).
// Indentation: 2 spaces. Docs in English.

function mapLevel(lvl) {
  const m = {
    debug: 'secondary',
    info: 'info',
    success: 'success',
    warning: 'warning',
    error: 'danger',
    secondary: 'secondary' // explicit support if backend sends "secondary"
  };
  return m[lvl] || 'info';
}

/**
 * Default auto-dismiss durations in milliseconds per level.
 * Set to 0 to disable auto-dismiss for that level.
 */
const defaultTimeouts = {
  debug: 10000,    // 10s
  info: 20000,     // 20s
  success: 20000,  // 20s
  warning: 30000,  // 30s
  error: 60000,    // 60s
  secondary: 10000 // treat like debug
};

/**
 * Normalize different backend message shapes into a unified array:
 *   { level, text }
 *   { level, message }
 *   { level, rendered }
 */
export function normalize(response) {
  if (!response) return [];
  const out = [];

  // single top-level string message
  if (typeof response?.message === 'string') {
    out.push({ level: 'info', text: response.message });
  }

  // array of messages
  if (Array.isArray(response?.messages)) {
    response.messages.forEach(m => {
      if (!m) return;

      if (typeof m === 'string') {
        out.push({ level: 'info', text: m });
      } else if (typeof m === 'object') {
        const text = m.text || m.message || '';
        if (text) {
          out.push({ level: (m.level || 'info').toLowerCase(), text });
        } else if (m.rendered) {
          // pass along raw HTML
          out.push({ level: (m.level || 'info').toLowerCase(), text: m.rendered, rendered: true });
        }
      }
    });
  }

  return out;
}

/**
 * Render a list of normalized messages as Bootstrap alerts.
 * If a message has { rendered: true }, its HTML is inserted directly.
 * Additionally, each message is logged to console.debug.
 *
 * @param {Array} list - normalized messages
 * @param {Object} opts - render options
 * @param {string|Element} opts.container - target element/selector
 * @param {boolean} opts.dismissible - allow manual close
 * @param {boolean} opts.clearBefore - clear existing messages
 * @param {Object} opts.timeouts - optional override per level in ms
 */
export function render(
  list,
  { container, dismissible = true, clearBefore = true, timeouts = {} } = {}
) {
  if (!container) return;
  const host =
    typeof container === 'string'
      ? document.querySelector(container)
      : container;
  if (!host) return;
  if (clearBefore) host.replaceChildren();

  list.forEach(({ text, level = 'info', rendered }) => {
    // Log every message to console.debug
    console.debug('[cmnsd:message]', { level, text, rendered });

    if (rendered) {
      // Insert server-provided HTML directly
      host.insertAdjacentHTML('beforeend', text);
      return;
    }

    const div = document.createElement('div');
    div.className = `alert alert-${mapLevel(level)}`;
    div.setAttribute('role', 'alert');

    if (dismissible) {
      div.classList.add('alert-dismissible', 'fade', 'show');
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn-close';
      btn.setAttribute('data-bs-dismiss', 'alert');
      btn.setAttribute('aria-label', 'Close');
      div.appendChild(btn);
    }

    const span = document.createElement('span');
    span.innerHTML = String(text);
    div.prepend(span);
    host.appendChild(div);

    // Auto-dismiss timer
    const timeout =
      typeof timeouts[level] === 'number'
        ? timeouts[level]
        : defaultTimeouts[level] ?? 0;
    if (timeout > 0) {
      setTimeout(() => {
        if (div && div.parentNode) {
          div.classList.remove('show');
          // remove after fade transition if using Bootstrap
          setTimeout(() => div.remove(), 150);
        }
      }, timeout);
    }
  });
}