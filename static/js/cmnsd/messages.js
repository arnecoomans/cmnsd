// Bootstrap alert helpers (normalize + render).
// Indentation: 2 spaces. Docs in English.

function mapLevel(lvl) {
  const m = {
    debug: 'secondary',
    info: 'info',
    success: 'success',
    warning: 'warning',
    error: 'danger',
    secondary: 'secondary'
  };
  return m[lvl] || 'info';
}

const defaultTimeouts = {
  debug: 10000,    // 10s
  info: 20000,     // 20s
  success: 20000,  // 20s
  warning: 30000,  // 30s
  error: 60000,    // 60s
  secondary: 10000
};

export function normalize(response) {
  if (!response) return [];
  const out = [];

  if (typeof response?.message === 'string') {
    out.push({ level: 'info', text: response.message });
  }

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
          out.push({
            level: (m.level || 'info').toLowerCase(),
            text: m.rendered,
            rendered: true
          });
        }
      }
    });
  }

  return out;
}

/**
 * Render messages as Bootstrap alerts.
 * By default, new messages are *appended* (clearBefore=false).
 * Max stack size enforced via opts.max (default 5).
 */
export function render(
  list,
  { container, dismissible = true, clearBefore = false, timeouts = {}, max = 5 } = {}
) {
  if (!container) return;
  const host =
    typeof container === 'string'
      ? document.querySelector(container)
      : container;
  if (!host) return;

  if (clearBefore) host.replaceChildren();

  list.forEach(({ text, level = 'info', rendered }) => {
    console.debug('[cmnsd:message]', { level, text, rendered });

    if (rendered) {
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

    // Auto-dismiss
    const timeout =
      typeof timeouts[level] === 'number'
        ? timeouts[level]
        : defaultTimeouts[level] ?? 0;
    if (timeout > 0) {
      setTimeout(() => {
        if (div && div.parentNode) {
          div.classList.remove('show');
          setTimeout(() => div.remove(), 300); // match CSS transition
        }
      }, timeout);
    }
  });

  // Enforce max stack size
  const alerts = host.querySelectorAll('.alert');
  if (alerts.length > max) {
    const excess = alerts.length - max;
    for (let i = 0; i < excess; i++) {
      alerts[i].remove(); // remove oldest (top-most)
    }
  }
}
