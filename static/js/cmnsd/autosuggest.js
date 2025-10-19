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
  const prefix = host.dataset.fieldPrefix || '';
  const followMode = host.dataset.onclickFollow === 'url'; // ✅ new
  const displayFields = (host.dataset.displayFields || inputKey)
    .split(',')
    .map(s => s.trim());
  const secondaryScale = parseFloat(host.dataset.displaySecondarySize || '0.8');

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
  let activeIndex = -1; // ✅ keyboard navigation state
  let itemsRef = []; // ✅ keep references to suggestion buttons

  function clearList(empty = false) {
    list.innerHTML = '';
    list.style.display = empty ? 'block' : 'none';
    list.classList.toggle('empty', empty);
    activeIndex = -1;
    itemsRef = [];
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

  // Ensure only one field submits
  function syncFieldNames() {
    if (hiddenVal.value) {
      host.removeAttribute('name');
      hiddenVal.name = prefix + hiddenKey;
      hiddenName.removeAttribute('name');
    } else if (host.value.trim() !== '') {
      host.name = prefix + inputKey;
      hiddenVal.removeAttribute('name');
    } else {
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

  // ✅ Enhanced suggestion rendering
  function renderSuggestions(items) {
    clearList();
    itemsRef = [];

    items.forEach((item, index) => {
      const mainField = displayFields[0];
      const secondaryFields = displayFields.slice(1);

      const el = document.createElement('button');
      el.type = 'button';
      el.className = 'list-group-item list-group-item-action text-start';

      // --- Main line ---
      const mainValue = item[mainField] ?? '';
      const mainSpan = document.createElement('div');
      mainSpan.className = 'autosuggest-main';
      mainSpan.appendChild(sanitizeHTML(mainValue));
      el.appendChild(mainSpan);

      // --- Secondary lines ---
      secondaryFields.forEach(fld => {
        const val = item[fld];
        if (val) {
          const subSpan = document.createElement('div');
          subSpan.className = 'autosuggest-secondary';
          subSpan.style.fontSize = `${secondaryScale * 100}%`;
          subSpan.style.opacity = '0.8';
          subSpan.appendChild(sanitizeHTML(val));
          el.appendChild(subSpan);
        }
      });

      const submitVal = item[hiddenKey] ?? null;

      // --- click behavior ---
      el.addEventListener('click', e => {
        e.preventDefault();
        e.stopPropagation();

        // Follow mode
        if (followMode && item.url) {
          console.debug('[cmnsd:autosuggest] follow mode → navigating to', item.url);
          window.location.href = item.url;
          return;
        }

        // Normal insert/update
        host.value = mainValue.replace(/<[^>]*>/g, '');
        if (submitVal) {
          hiddenVal.value = submitVal;
          hiddenName.value = '';
        } else if (allowCreate) {
          hiddenVal.value = '';
          hiddenName.value = host.value;
        }

        syncFieldNames();
        clearList();
        updateValidity();
      });

      list.appendChild(el);
      itemsRef.push(el);
    });

    list.style.display = 'block';
  }

  // ✅ Keyboard navigation
  host.addEventListener('keydown', e => {
    if (!itemsRef.length) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIndex = (activeIndex + 1) % itemsRef.length;
      updateActiveItem();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIndex = (activeIndex - 1 + itemsRef.length) % itemsRef.length;
      updateActiveItem();
    } else if (e.key === 'Enter') {
      if (activeIndex >= 0 && itemsRef[activeIndex]) {
        e.preventDefault();
        itemsRef[activeIndex].click();
      }
    } else if (e.key === 'Escape') {
      clearList();
    }
  });

  function updateActiveItem() {
    itemsRef.forEach((el, i) => {
      if (i === activeIndex) el.classList.add('active');
      else el.classList.remove('active');
    });
    const activeEl = itemsRef[activeIndex];
    if (activeEl) {
      activeEl.scrollIntoView({ block: 'nearest' });
    }
  }

  // Input handler
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