// Autosuggest feature for cmnsd
// Indentation: 2 spaces. Docs in English.

import { api } from './http.js';

function setupInput(host) {
  if (host.hasAttribute('data-autosuggestActive')) {
    host.removeAttribute('data-autosuggestActive');
  }

  if (host.dataset.autosuggestActive) {
    console.debug('[cmnsd:autosuggest] skip already active', host);
    return;
  }
  host.dataset.autosuggestActive = '1';

  // Remove stray attributes that would conflict
  const strayAttrs = ['action', 'method', 'map', 'body', 'disable', 'confirm'];
  strayAttrs.forEach(attr => {
    const key = 'data-' + attr;
    if (host.hasAttribute(key)) {
      console.debug('[cmnsd:autosuggest] removing stray', key, 'on', host);
      host.removeAttribute(key);
    }
  });
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
  const allowCreate = host.dataset.allowCreate !== '0'; // default true

  if (!url) {
    console.warn('[cmnsd:autosuggest] missing data-url for', host);
    return;
  }

  // Ensure host has no name
  host.removeAttribute('name');

  // Hidden fields
  let hiddenVal = host.parentNode.querySelector(
    `input[type="hidden"][name="${hiddenKey}"]`
  );
  if (!hiddenVal) {
    hiddenVal = document.createElement('input');
    hiddenVal.type = 'hidden';
    hiddenVal.name = hiddenKey;
    host.parentNode.appendChild(hiddenVal);
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

  // Suggestion dropdown
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

  function updateValidity() {
    const form = host.closest('form');
    if (!form) return;
    const submitBtn = form.querySelector('[type=submit]');
    if (!submitBtn) return;

    if (!allowCreate) {
      // enforce valid suggestion only
      if (hiddenVal.value && host.value.trim() !== '') {
        submitBtn.disabled = false;
      } else {
        submitBtn.disabled = true;
      }
    } else {
      // free text allowed, but not empty
      if (host.value.trim() !== '') {
        submitBtn.disabled = false;
      } else {
        submitBtn.disabled = true;
      }
    }
  }

  async function fetchSuggestions(q) {
    try {
      const params = {};
      if (paramName) params[paramName] = q;

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

      if (containerKey && data && typeof data === 'object') {
        data = data[containerKey];
      }
      if (data && !Array.isArray(data) && typeof data === 'object') {
        data = Object.values(data);
      }

      if (!Array.isArray(data) || data.length === 0) {
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
      el.textContent = display;

      el.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        host.value = display;
        if (submitVal) {
          hiddenVal.value = submitVal;
          hiddenName.value = '';
        } else if (allowCreate) {
          hiddenVal.value = '';
          hiddenName.value = display;
        }
        clearList();
        updateValidity();
      });

      list.appendChild(el);
    });
    list.style.display = 'block';
  }

  // Input handler
  host.addEventListener('input', () => {
    console.debug('[cmnsd:autosuggest] input event', host.value);
    const q = host.value.trim();

    hiddenVal.value = '';
    hiddenName.value = allowCreate ? q : '';

    updateValidity();

    if (q.length < minChars) {
      if (minChars === 0) {
        fetchSuggestions('');
      } else {
        clearList();
      }
      return;
    }
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fetchSuggestions(q), debounce);
  });

  // Show all options when focused if minChars=0
  host.addEventListener('focus', () => {
    if (minChars === 0) {
      fetchSuggestions('');
    }
  });

  host.addEventListener('blur', () => {
    setTimeout(() => clearList(), 200);
  });

  // Initial validity check
  updateValidity();

  console.debug('[cmnsd:autosuggest] bound to input', host, { minChars, allowCreate });
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
  console.debug(
    '[cmnsd:autosuggest] content applied event fired from',
    e.detail?.container || e.target
  );
  initAutosuggest(document);
});
