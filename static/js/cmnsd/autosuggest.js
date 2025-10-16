// Autosuggest feature for cmnsd
// Indentation: 2 spaces. Docs in English.

import { api } from './http.js';

function sanitizeHTML(input, allowedTags = ['B', 'STRONG', 'I', 'EM']) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(input, 'text/html');
  const fragment = document.createDocumentFragment();

  function walk(node, parent) {
    node.childNodes.forEach(child => {
      if (child.nodeType === Node.TEXT_NODE) {
        parent.appendChild(document.createTextNode(child.textContent));
      } else if (child.nodeType === Node.ELEMENT_NODE) {
        if (allowedTags.includes(child.tagName)) {
          const safeEl = document.createElement(child.tagName.toLowerCase());
          walk(child, safeEl);
          parent.appendChild(safeEl);
        } else {
          parent.appendChild(document.createTextNode(child.textContent));
        }
      }
    });
  }

  walk(doc.body, fragment);
  return fragment;
}

function setupInput(host) {
  if (host.dataset.autosuggestActive) return;
  host.dataset.autosuggestActive = '1';

  // Clean up conflicting attributes
  const strayAttrs = ['action', 'method', 'map', 'body', 'disable', 'confirm', 'action'];
  strayAttrs.forEach(attr => {
    const key = 'data-' + attr;
    if (host.hasAttribute(key)) host.removeAttribute(key);
  });

  const url = host.dataset.url;
  const minChars = parseInt(host.dataset.min || '2', 10);
  const debounce = parseInt(host.dataset.debounce || '300', 10);
  const paramName = host.dataset.param || 'q';
  const inputKey = host.dataset.fieldInput || 'name';
  const hiddenKey = host.dataset.fieldHidden || 'slug';
  const containerKey = host.dataset.container || null;
  const allowCreate = host.dataset.allowCreate !== '0';
  const isSearchMode = host.dataset.searchMode === 'true';
  const prefix = host.dataset.fieldPrefix || '';

  if (!url) {
    console.warn('[cmnsd:autosuggest] missing data-url for', host);
    return;
  }

  // Hidden fields
  let hiddenVal = host.parentNode.querySelector(
    `input[type="hidden"][name="${prefix}${hiddenKey}"]`
  );
  if (!hiddenVal) {
    hiddenVal = document.createElement('input');
    hiddenVal.type = 'hidden';
    hiddenVal.name = prefix + hiddenKey;
    host.parentNode.appendChild(hiddenVal);
  }

  let hiddenName = host.parentNode.querySelector(
    `input[type="hidden"][name="${prefix}${inputKey}"]`
  );
  if (!hiddenName) {
    hiddenName = document.createElement('input');
    hiddenName.type = 'hidden';
    hiddenName.name = prefix + inputKey;
    host.parentNode.appendChild(hiddenName);
  }

  // Suggestion list
  const list = document.createElement('div');
  list.className = 'cmnsd-autosuggest list-group position-absolute w-100';
  list.style.zIndex = 2000;
  host.parentNode.style.position = 'relative';
  host.parentNode.appendChild(list);

  let timer = null;

  function clearList(empty = false) {
    list.innerHTML = '';
    list.style.display = empty ? 'block' : 'none';
    list.classList.toggle('empty', empty);
  }

  function updateValidity() {
    const form = host.closest('form');
    if (!form) return;
    const submitBtn = form.querySelector('[type=submit]');
    if (!submitBtn) return;

    const hasHidden = hiddenVal.value && host.value.trim() !== '';
    const hasText = host.value.trim() !== '';

    if (!allowCreate) {
      submitBtn.disabled = !hasHidden;
    } else {
      submitBtn.disabled = !hasText;
    }
  }

  // Ensure only one field submits:
  function syncFieldNames() {
    if (hiddenVal.value) {
      // A suggestion was chosen → only submit the hidden field
      if (!isSearchMode) host.removeAttribute('name');
      hiddenVal.name = prefix + hiddenKey;
      hiddenName.removeAttribute('name');
    } else if (host.value.trim() !== '') {
      // Free text typed → only submit the input field
      if (isSearchMode) {
        // Keep name='q' for search
        host.name = 'q';
      } else {
        host.name = prefix + inputKey;
      }
      hiddenVal.removeAttribute('name');
    } else {
      // Nothing entered → disable all
      host.removeAttribute('name');
      hiddenVal.removeAttribute('name');
    }
  }

  async function fetchSuggestions(q) {
    try {
      const params = {};
      if (paramName) params[paramName] = q;

      if (host.dataset.extraParams) {
        try {
          Object.assign(params, JSON.parse(host.dataset.extraParams));
        } catch (err) {
          console.warn('[cmnsd:autosuggest] invalid data-extra-params JSON', err);
        }
      }

      const res = await api.get(url, { params });
      let data = res?.payload || [];

      if (containerKey && data && typeof data === 'object') {
        data = data[containerKey];
      }
      if (data && !Array.isArray(data) && typeof data === 'object') {
        data = Object.values(data);
      }

      if (!Array.isArray(data) || !data.length) {
        clearList(true);
        hiddenVal.value = '';
        updateValidity();
        return;
      }

      renderSuggestions(data);
    } catch (err) {
      console.warn('[cmnsd:autosuggest] fetch failed', err);
      clearList(true);
      hiddenVal.value = '';
      updateValidity();
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
      el.appendChild(sanitizeHTML(display));

      el.addEventListener('click', e => {
        e.preventDefault();
        e.stopPropagation();

        host.value = display.replace(/<[^>]*>/g, '');
        if (submitVal) {
          // Suggestion chosen → keep only hidden
          hiddenVal.value = submitVal;
          hiddenName.value = '';
        } else if (allowCreate) {
          // New text → keep only visible
          hiddenVal.value = '';
          hiddenName.value = host.value;
        }

        syncFieldNames();
        clearList();
        updateValidity();
      });

      list.appendChild(el);
    });
    list.style.display = 'block';
  }

  host.addEventListener('input', () => {
    const q = host.value.trim();
    hiddenVal.value = '';
    hiddenName.value = allowCreate ? q : '';
    syncFieldNames();
    updateValidity();

    if (q.length < minChars) {
      if (minChars === 0) fetchSuggestions('');
      else clearList();
      return;
    }
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fetchSuggestions(q), debounce);
  });

  host.addEventListener('focus', () => {
    if (minChars === 0) fetchSuggestions('');
  });

  host.addEventListener('blur', () => {
    setTimeout(() => clearList(), 200);
  });

  // Ensure consistency before submit
  const form = host.closest('form');
  if (form) {
    form.addEventListener('submit', () => syncFieldNames());
  }

  updateValidity();
  syncFieldNames();

  console.debug('[cmnsd:autosuggest] bound to input', host, { minChars, allowCreate, prefix });
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

document.addEventListener('DOMContentLoaded', () => {
  console.debug('[cmnsd:autosuggest] DOMContentLoaded fired');
  initAutosuggest();
});

document.addEventListener('cmnsd:content:applied', e => {
  console.debug('[cmnsd:autosuggest] content applied event fired from', e.detail?.container || e.target);
  initAutosuggest(document);
});
