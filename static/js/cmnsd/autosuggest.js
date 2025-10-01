// Autosuggest feature for cmnsd
// Indentation: 2 spaces. Docs in English.

import { api } from './http.js';

function setupInput(host) {
  // Clean leftover attribute (e.g. from server-rendered HTML)
  if (host.hasAttribute('data-autosuggestActive')) {
    host.removeAttribute('data-autosuggestActive');
  }

  if (host.dataset.autosuggestActive) {
    console.debug('[cmnsd:autosuggest] skip already active', host);
    return;
  }
  host.dataset.autosuggestActive = '1';

  // Ignore stray action-related attributes (remove from autosuggest inputs)
  const strayAttrs = [
    'action',
    'method',
    'map',
    'body',
    'disable',
    'confirm'
  ];
  strayAttrs.forEach(attr => {
    const key = 'data-' + attr;
    if (host.hasAttribute(key)) {
      console.debug('[cmnsd:autosuggest] removing stray', key, 'on', host);
      host.removeAttribute(key);
    }
  });

  // Explicitly remove data-action if present
  if (host.hasAttribute('data-action')) {
    console.debug('[cmnsd:autosuggest] removing stray data-action on', host);
    host.removeAttribute('data-action');
  }

  const url = host.dataset.url;
  const minChars = parseInt(host.dataset.min || '2', 10);
  const debounce = parseInt(host.dataset.debounce || '300', 10);
  const paramName = host.dataset.param || 'q';
  const inputKey = host.dataset.fieldInput || 'name';
  const hiddenKey = host.dataset.fieldHidden || 'slug';
  const containerKey = host.dataset.container || null;

  if (!url) {
    console.warn('[cmnsd:autosuggest] missing data-url for', host);
    return;
  }

  // Ensure host has no name (so it won’t submit)
  host.removeAttribute('name');

  // Hidden fields: reuse if present, else create
  let hiddenSlug = host.parentNode.querySelector(
    `input[type="hidden"][name="${hiddenKey}"]`
  );
  if (!hiddenSlug) {
    hiddenSlug = document.createElement('input');
    hiddenSlug.type = 'hidden';
    hiddenSlug.name = hiddenKey;
    host.parentNode.appendChild(hiddenSlug);
  }

  let hiddenName = host.parentNode.querySelector(
    `input[type="hidden"][name="${inputKey}"]`
  );
  if (!hiddenName) {
    hiddenName = document.createElement('input');
    hiddenName.type = 'hidden';
    hiddenName.name = inputKey;
    host.parentNode.appendChild(hiddenName);
  }

  // Suggestion dropdown container
  const list = document.createElement('div');
  list.className = 'cmnsd-autosuggest list-group position-absolute w-100';
  list.style.zIndex = 2000;
  host.parentNode.style.position = 'relative';
  host.parentNode.appendChild(list);

  let timer = null;

  function clearList(empty = false) {
    list.innerHTML = '';
    if (empty) {
      list.classList.add('empty');
      list.style.display = 'block';
    } else {
      list.classList.remove('empty');
      list.style.display = 'none';
    }
  }

  async function fetchSuggestions(q) {
    try {
      const params = { [paramName]: q };

      if (host.dataset.extraParams) {
        try {
          const extra = JSON.parse(host.dataset.extraParams);
          Object.assign(params, extra);
        } catch (err) {
          console.warn('[cmnsd:autosuggest] invalid data-extra-params JSON', err);
        }
      }

      const res = await api.get(url, { params });
      let data = res?.payload || [];

      // Navigate into container key if set
      if (containerKey && data && typeof data === 'object') {
        data = data[containerKey];
      }

      // If object, convert to array
      if (data && !Array.isArray(data) && typeof data === 'object') {
        data = Object.values(data);
      }

      if (!Array.isArray(data) || data.length === 0) {
        clearList(true);
        return;
      }

      renderSuggestions(data);
    } catch (err) {
      console.warn('[cmnsd:autosuggest] fetch failed', err);
      clearList(true);
    }
  }

  function renderSuggestions(items) {
    clearList();
    items.forEach(item => {
      const display = item[inputKey] ?? '';
      const submitVal = item[hiddenKey] ?? null;

      const el = document.createElement('button');
      el.type = 'button';
      el.className = 'list-group-item list-group-item-action';
      el.textContent = display;

      el.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        host.value = display;
        if (submitVal) {
          hiddenSlug.value = submitVal;
          hiddenName.value = '';
        } else {
          hiddenSlug.value = '';
          hiddenName.value = display;
        }
        clearList();
      });

      list.appendChild(el);
    });
    list.style.display = 'block';
  }

  // Debounced input handler
  host.addEventListener('input', () => {
    console.debug('[cmnsd:autosuggest] input event', host.value);
    const q = host.value.trim();
    hiddenSlug.value = '';
    hiddenName.value = q;
    if (q.length < minChars) {
      clearList();
      return;
    }
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fetchSuggestions(q), debounce);
  });

  // Hide dropdown on blur
  host.addEventListener('blur', () => {
    setTimeout(() => clearList(), 200);
  });

  console.debug('[cmnsd:autosuggest] bound to input', host);
}

export function initAutosuggest(root = document) {
  const found = root.querySelectorAll('input[data-autosuggest]');
  console.debug('[cmnsd:autosuggest] scanning', root, 'found', found.length);
  found.forEach(el => {
    try {
      setupInput(el);
    } catch (err) {
      console.error('[cmnsd:autosuggest] setup failed for', el, err);
    }
  });
}

// Initial scan
document.addEventListener('DOMContentLoaded', () => {
  console.debug('[cmnsd:autosuggest] DOMContentLoaded fired');
  initAutosuggest();
});

// Always rescan the full document after content loads
document.addEventListener('cmnsd:content:applied', e => {
  console.debug(
    '[cmnsd:autosuggest] content applied event fired from',
    e.detail?.container || e.target
  );
  initAutosuggest(document);
});
