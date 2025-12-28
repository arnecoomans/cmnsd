// Autosuggest feature for cmnsd
// Version 2.6 — with AbortController support
// Indentation: 2 spaces. Docs in English.

import { api } from './http.js';

/**
 * Sanitize limited inline HTML (e.g. <b>, <i>).
 * Converts everything else to plain text.
 */
function sanitizeHTML(input, allowedTags = ['B', 'STRONG', 'I', 'EM']) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(String(input ?? ''), 'text/html');
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

/** Overlay root for dropdowns (portal) */
function getOverlayRoot() {
  let overlay = document.getElementById('cmnsd-overlays');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'cmnsd-overlays';
    overlay.style.position = 'absolute';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100%';
    overlay.style.height = '0';
    overlay.style.zIndex = '3000';
    overlay.style.pointerEvents = 'none';
    document.body.appendChild(overlay);
  }
  return overlay;
}

function setupInput(host) {
  if (host.dataset.autosuggestActive) return;
  host.dataset.autosuggestActive = '1';

  // 🆕 Abort controller per input
  let abortController = null;

  // Clean stray action-like attributes
  ['action', 'method', 'map', 'body', 'disable', 'confirm', 'action'].forEach(attr => {
    const key = 'data-' + attr;
    if (host.hasAttribute(key)) host.removeAttribute(key);
  });
  if (host.hasAttribute('data-action')) host.removeAttribute('data-action');

  const url = host.dataset.url;
  const localSource = host.dataset.localSource;
  const minChars = parseInt(host.dataset.min || '2', 10);
  const debounceMs = parseInt(host.dataset.debounce || '300', 10);
  const paramName = host.dataset.param || 'q';
  const inputKey = host.dataset.fieldInput || 'name';
  const hiddenKey = host.dataset.fieldHidden || null;
  const containerKey = host.dataset.container || null;
  const allowCreate = host.dataset.allowCreate !== '0';
  const prefix = host.dataset.fieldPrefix || '';
  const followMode = host.dataset.onclickFollow === 'url';
  const displayFields = (host.dataset.displayFields || inputKey)
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);
  const secondaryScale = parseFloat(host.dataset.displaySecondarySize || '0.8');
  const uniqueKey = host.dataset.forceUnique || null;
  const sourceKey = host.dataset.sourceField || inputKey;
  const isSearchMode = host.dataset.searchMode === 'true';

  // Hidden fields
  let hiddenVal = null;
  let hiddenName = null;

  if (hiddenKey) {
    const form = host.closest('form');
    const scope = form || host.parentNode;

    hiddenVal = scope.querySelector(`input[type="hidden"][name="${prefix}${hiddenKey}"]`);
    if (!hiddenVal) {
      hiddenVal = document.createElement('input');
      hiddenVal.type = 'hidden';
      hiddenVal.name = prefix + hiddenKey;
      hiddenVal.value = '';
      if (form) form.appendChild(hiddenVal);
      else scope.appendChild(hiddenVal);
    }

    hiddenName = scope.querySelector(`input[type="hidden"][name="${prefix}${inputKey}"]`);
    if (!hiddenName) {
      hiddenName = document.createElement('input');
      hiddenName.type = 'hidden';
      hiddenName.name = prefix + inputKey;
      hiddenName.value = '';
      if (form) form.appendChild(hiddenName);
      else scope.appendChild(hiddenName);
    }
  }

  const overlayRoot = getOverlayRoot();
  const list = document.createElement('div');
  list.className = 'cmnsd-autosuggest list-group position-absolute';
  list.style.zIndex = 3001;
  list.style.pointerEvents = 'auto';
  list.style.display = 'none';
  overlayRoot.appendChild(list);

  let activeIndex = -1;
  let itemsRef = [];

  function positionList() {
    const rect = host.getBoundingClientRect();
    list.style.top = `${rect.bottom + window.scrollY}px`;
    list.style.left = `${rect.left + window.scrollX}px`;
    list.style.width = `${rect.width}px`;
  }

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
    const submit = form.querySelector('[type=submit]');
    if (!submit) return;

    if (form.dataset.autosuggestAllowEmpty === '1') {
      submit.disabled = false;
      return;
    }

    const hasHidden = hiddenVal && !!hiddenVal.value && host.value.trim() !== '';
    const hasText = host.value.trim() !== '';
    submit.disabled = !allowCreate ? !hasHidden : !hasText;
  }

  function syncFieldNames() {
    if (!hiddenVal) return;
    if (hiddenVal.value) {
      if (!isSearchMode) host.removeAttribute('name');
      hiddenVal.name = prefix + hiddenKey;
      if (hiddenName) hiddenName.removeAttribute('name');
    } else if (host.value.trim() !== '') {
      host.name = isSearchMode ? 'q' : prefix + inputKey;
      hiddenVal.removeAttribute('name');
    } else {
      host.removeAttribute('name');
      hiddenVal.removeAttribute('name');
    }
  }

  async function fetchSuggestions(q) {
    try {
      // 🆕 Abort previous request
      if (abortController) {
        abortController.abort();
      }
      abortController = new AbortController();

      const params = {};
      if (paramName) params[paramName] = q;
      if (host.dataset.extraParams) {
        try { Object.assign(params, JSON.parse(host.dataset.extraParams)); }
        catch {}
      }

      const res = await api.get(url, {
        params,
        signal: abortController.signal
      });

      let data = res?.payload || [];
      if (containerKey && data && typeof data === 'object') data = data[containerKey];
      if (data && !Array.isArray(data) && typeof data === 'object') data = Object.values(data);

      if (uniqueKey && Array.isArray(data)) {
        const seen = new Set();
        const keys = uniqueKey.split(',').map(k => k.trim());
        data = data.filter(it => {
          const combo = keys.map(k => String(it?.[k] || '').toLowerCase()).join('|');
          if (!seen.has(combo)) { seen.add(combo); return true; }
          return false;
        });
      }

      if (!Array.isArray(data) || !data.length) {
        clearList(true);
        if (hiddenVal) hiddenVal.value = '';
        updateValidity();
        return;
      }

      renderSuggestions(data);

    } catch (err) {
      // 🆕 Abort is expected behavior
      if (err.name === 'AbortError') return;

      console.warn('[cmnsd:autosuggest] fetch failed', err);
      clearList(true);
      if (hiddenVal) hiddenVal.value = '';
      updateValidity();
    }
  }

  function renderSuggestions(items) {
    list.innerHTML = '';
    itemsRef = [];
    positionList();

    items.forEach(item => {
      const el = document.createElement('button');
      el.type = 'button';
      el.className = 'list-group-item list-group-item-action text-start';

      const mainField = displayFields[0] || sourceKey;
      const secondaryFields = displayFields.slice(1);
      const mainValue = item[mainField] ?? '';

      const mainDiv = document.createElement('div');
      mainDiv.className = 'autosuggest-main';
      mainDiv.appendChild(sanitizeHTML(mainValue));
      el.appendChild(mainDiv);

      secondaryFields.forEach(f => {
        const val = item[f];
        if (val) {
          const sub = document.createElement('div');
          sub.className = 'autosuggest-secondary';
          sub.style.fontSize = `${secondaryScale * 100}%`;
          sub.style.opacity = '0.8';
          sub.appendChild(sanitizeHTML(val));
          el.appendChild(sub);
        }
      });

      el.addEventListener('click', e => {
        e.preventDefault();
        e.stopPropagation();

        if (followMode && item.url) {
          window.location.href = item.url;
          return;
        }

        const displayVal = String(item[sourceKey] || mainValue).replace(/<[^>]*>/g, '');
        const hiddenFieldVal = item[hiddenKey] ?? '';

        host.value = displayVal;

        if (hiddenVal) {
          hiddenVal.name = prefix + hiddenKey;
          hiddenVal.value = hiddenFieldVal;
        }
        if (hiddenName) {
          hiddenName.name = prefix + inputKey;
          hiddenName.value = displayVal;
        }

        list.style.display = 'none';
        updateValidity();
      });

      list.appendChild(el);
      itemsRef.push(el);
    });

    activeIndex = -1;
    list.style.display = 'block';
  }

  host.addEventListener('keydown', e => {
    if (list.style.display !== 'block' || !itemsRef.length) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIndex = (activeIndex + 1) % itemsRef.length;
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIndex = (activeIndex - 1 + itemsRef.length) % itemsRef.length;
    } else if (e.key === 'Enter') {
      if (activeIndex >= 0 && itemsRef[activeIndex]) {
        e.preventDefault();
        itemsRef[activeIndex].click();
      }
    } else if (e.key === 'Escape') {
      clearList();
    }
    itemsRef.forEach((el, i) => el.classList.toggle('active', i === activeIndex));
  });

  let debounceTimer = null;
  host.addEventListener('input', () => {
    const q = host.value.trim();
    if (hiddenVal) hiddenVal.value = '';
    if (hiddenName) hiddenName.value = allowCreate ? q : '';
    updateValidity();

    if (q.length < minChars) {
      if (minChars === 0) fetchSuggestions('');
      else clearList();
      return;
    }

    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => fetchSuggestions(q), debounceMs);
  });

  host.addEventListener('focus', () => {
    if (minChars === 0) fetchSuggestions('');
  });

  host.addEventListener('blur', () => {
    setTimeout(() => clearList(), 200);
  });

  const form = host.closest('form');
  if (form) {
    form.addEventListener('submit', () => {
      if (hiddenVal) syncFieldNames();
    });
  }

  updateValidity();
  if (hiddenVal) syncFieldNames();
}

export function initAutosuggest(root = document) {
  const found = root.querySelectorAll('input[data-autosuggest]');
  found.forEach(el => {
    try { setupInput(el); }
    catch (err) { console.error('[cmnsd:autosuggest] setup failed', el, err); }
  });
}

document.addEventListener('DOMContentLoaded', () => initAutosuggest());
document.addEventListener('cmnsd:content:applied', e => {
  initAutosuggest(e.detail?.container || document);
});