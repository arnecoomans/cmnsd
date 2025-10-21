// Autosuggest feature for cmnsd
// Indentation: 2 spaces. Docs in English.

import { api } from './http.js';

/**
 * Sanitize limited inline HTML coming from server (e.g. <b>, <i>).
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
    overlay.style.height = '0'; // don't block layout
    overlay.style.zIndex = '3000';
    overlay.style.pointerEvents = 'none'; // let clicks pass through when empty
    document.body.appendChild(overlay);
  }
  return overlay;
}

function setupInput(host) {
  if (host.dataset.autosuggestActive) return;
  host.dataset.autosuggestActive = '1';

  const stray = ['action', 'method', 'map', 'body', 'disable', 'confirm', 'action'];
  stray.forEach(attr => {
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
  const hiddenKey = host.dataset.fieldHidden || 'slug';
  const containerKey = host.dataset.container || null;
  const allowCreate = host.dataset.allowCreate !== '0';
  const prefix = host.dataset.fieldPrefix || '';
  const followMode = host.dataset.onclickFollow === 'url';
  const displayFields = (host.dataset.displayFields || inputKey)
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);
  const secondaryScale = parseFloat(host.dataset.displaySecondarySize || '0.8');
  const isSearchMode = host.dataset.searchMode === 'true';

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

  const overlayRoot = getOverlayRoot();
  const list = document.createElement('div');
  list.className = 'cmnsd-autosuggest list-group position-absolute';
  list.style.zIndex = 3001;
  list.style.pointerEvents = 'auto';
  list.style.display = 'none';
  overlayRoot.appendChild(list);

  let activeIndex = -1;
  let itemsRef = [];

  function dispatch(name, detail) {
    const ev = new CustomEvent(name, { bubbles: true, detail });
    (host || document).dispatchEvent(ev);
  }

  function positionList() {
    const rect = host.getBoundingClientRect();
    list.style.position = 'absolute';
    list.style.top = `${rect.bottom + window.scrollY}px`;
    list.style.left = `${rect.left + window.scrollX}px`;
    list.style.width = `${rect.width}px`;
    dispatch('cmnsd:autosuggest:positioned', { host });
  }

  const onScrollOrResize = () => {
    if (list.style.display === 'block') positionList();
  };
  window.addEventListener('scroll', onScrollOrResize, { passive: true });
  window.addEventListener('resize', onScrollOrResize, { passive: true });

  function clearList(empty = false) {
    list.innerHTML = '';
    list.style.display = empty ? 'block' : 'none';
    list.classList.toggle('empty', empty);
    activeIndex = -1;
    itemsRef = [];
    if (!empty) dispatch('cmnsd:autosuggest:hidden', { host });
  }

  function updateValidity() {
    const form = host.closest('form');
    if (!form) return;
    const submitBtn = form.querySelector('[type=submit]');
    if (!submitBtn) return;

    const hasHidden = !!hiddenVal.value && host.value.trim() !== '';
    const hasText = host.value.trim() !== '';

    if (!allowCreate) submitBtn.disabled = !hasHidden;
    else submitBtn.disabled = !hasText;
  }

  function syncFieldNames() {
    if (hiddenVal.value) {
      if (!isSearchMode) host.removeAttribute('name');
      hiddenVal.name = prefix + hiddenKey;
      hiddenName.removeAttribute('name');
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
      // --- Local source support ---
      if (localSource) {
        let listData = [];
        try {
          listData = JSON.parse(localSource);
        } catch {
          console.warn('[cmnsd:autosuggest] invalid JSON in data-local-source', host);
          return;
        }

        if (!Array.isArray(listData)) return clearList(true);

        const results = listData.filter(item => {
          const val = (typeof item === 'string' ? item : item[inputKey] || '').toLowerCase();
          return val.includes(q.toLowerCase());
        });

        if (!results.length) {
          clearList(true);
          return;
        }
        renderSuggestions(results);
        return;
      }

      // --- Remote fetch ---
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

      if (containerKey && data && typeof data === 'object') data = data[containerKey];
      if (data && !Array.isArray(data) && typeof data === 'object') data = Object.values(data);

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
    list.innerHTML = '';
    itemsRef = [];
    positionList();

    items.forEach((item, index) => {
      const el = document.createElement('button');
      el.type = 'button';
      el.className = 'list-group-item list-group-item-action text-start';

      const mainField = displayFields[0];
      const secondaryFields = displayFields.slice(1);
      const mainValue = item[mainField] ?? '';
      const mainSpan = document.createElement('div');
      mainSpan.className = 'autosuggest-main';
      mainSpan.appendChild(sanitizeHTML(mainValue));
      el.appendChild(mainSpan);

      secondaryFields.forEach(fld => {
        const val = item[fld];
        if (val) {
          const sub = document.createElement('div');
          sub.className = 'autosuggest-secondary';
          sub.style.fontSize = `${secondaryScale * 100}%`;
          sub.style.opacity = '0.8';
          sub.appendChild(sanitizeHTML(val));
          el.appendChild(sub);
        }
      });

      const submitVal = item[hiddenKey] ?? null;

      el.addEventListener('click', e => {
        e.preventDefault();
        e.stopPropagation();

        if (followMode && item.url) {
          window.location.href = item.url;
          return;
        }

        host.value = String(mainValue).replace(/<[^>]*>/g, '');
        if (submitVal) {
          hiddenVal.value = submitVal;
          hiddenName.value = '';
        } else if (allowCreate) {
          hiddenVal.value = '';
          hiddenName.value = host.value;
        }

        syncFieldNames();
        list.style.display = 'none';
        updateValidity();
        dispatch('cmnsd:autosuggest:selected', { host, item });
      });

      list.appendChild(el);
      itemsRef.push(el);
    });

    activeIndex = -1;
    list.style.display = 'block';
    dispatch('cmnsd:autosuggest:shown', { host });
  }

  // Keyboard navigation
  host.addEventListener('keydown', e => {
    if (list.style.display !== 'block' || !itemsRef.length) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIndex = (activeIndex + 1) % itemsRef.length;
      itemsRef.forEach((el, i) => el.classList.toggle('active', i === activeIndex));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIndex = (activeIndex - 1 + itemsRef.length) % itemsRef.length;
      itemsRef.forEach((el, i) => el.classList.toggle('active', i === activeIndex));
    } else if (e.key === 'Enter') {
      if (activeIndex >= 0 && itemsRef[activeIndex]) {
        e.preventDefault();
        itemsRef[activeIndex].click();
      }
    } else if (e.key === 'Escape') {
      clearList();
    }
  });

  // Input & focus behavior
  let debounceTimer = null;
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
  if (form) form.addEventListener('submit', () => syncFieldNames());

  updateValidity();
  syncFieldNames();
}

export function initAutosuggest(root = document) {
  const found = root.querySelectorAll('input[data-autosuggest]');
  found.forEach(el => {
    try {
      setupInput(el);
    } catch (err) {
      console.error('[cmnsd:autosuggest] setup failed for', el, err);
    }
  });
}

document.addEventListener('DOMContentLoaded', () => initAutosuggest());
document.addEventListener('cmnsd:content:applied', e => {
  const root = e.detail?.container || document;
  initAutosuggest(root);
});