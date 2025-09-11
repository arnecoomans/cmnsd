// Bootstrap alert helpers (normalize + render).
// Indentation: 2 spaces. Docs in English.

function mapLevel(lvl) {
  const m = { debug: 'secondary', info: 'info', success: 'success', warning: 'warning', error: 'danger' };
  return m[lvl] || 'info';
}

export function normalize(response) {
  if (!response) return [];
  const out = [];
  if (typeof response?.message === 'string') out.push({ level: 'info', text: response.message });
  if (Array.isArray(response?.messages)) {
    response.messages.forEach(m => {
      if (typeof m === 'string') out.push({ level: 'info', text: m });
      else if (m && typeof m.text === 'string') out.push({ level: mapLevel(m.level), text: m.text });
    });
  }
  return out;
}

export function render(list, { container, dismissible = true, clearBefore = true } = {}) {
  if (!container) return;
  const host = typeof container === 'string' ? document.querySelector(container) : container;
  if (!host) return;
  if (clearBefore) host.replaceChildren();
  list.forEach(({ text, level = 'info' }) => {
    const div = document.createElement('div');
    div.className = `alert alert-${level}`;
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
  });
}
