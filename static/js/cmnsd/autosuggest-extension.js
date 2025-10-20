// Autosuggest extension for semantic cross-field matching.
// Indentation: 2 spaces. Docs in English.

import { api } from './http.js';

export function initAutosuggestSemanticLinker(config = {}) {
  const targets = config.targets || [
    { field: 'category', url: '/json/categories/', hidden: 'id', input: 'name', match: 'slug,name' },
    { field: 'chain', url: '/json/chains/', hidden: 'id', input: 'name', match: 'slug,name' },
  ];

  const debounce = (fn, delay = 400) => {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), delay);
    };
  };

  function normalizeWord(w) {
    // Only part after last ":" and lowercased
    return w.trim().replace(/[:]+/g, ' ').split(' ').pop().toLowerCase();
  }

  async function tryMatchWord(word, target) {
    try {
      const res = await api.get(target.url, { params: { q: word } });
      let data = res?.payload || [];
      if (typeof data === 'object' && !Array.isArray(data)) {
        data = Object.values(data);
      }
      if (!Array.isArray(data) || !data.length) return null;

      const matchFields = (target.match || target.input || 'name')
        .split(',')
        .map(f => f.trim());

      return data.find(item =>
        matchFields.some(f => (item[f] || '').toLowerCase() === word.toLowerCase())
      );
    } catch (err) {
      console.warn('[cmnsd:semantic] match fetch failed', err);
    }
    return null;
  }

  function highlight(el, color = '#d1e7dd') {
    if (!el) return;
    const original = el.style.backgroundColor;
    el.style.transition = 'background-color 0.3s ease';
    el.style.backgroundColor = color;
    setTimeout(() => {
      el.style.backgroundColor = original;
    }, 1000);
  }

  async function analyzeAndFill(sourceInput) {
    const text = sourceInput.value.trim();
    if (!text) return;

    const words = text.split(/\s+/).map(normalizeWord);

    for (const word of words) {
      for (const target of targets) {
        const match = await tryMatchWord(word, target);
        if (match) {
          const hiddenSelector = `input[type="hidden"][name*="${target.field}__"]`;
          const visibleSelector = `input[data-autosuggest][data-url*="${target.url}"]`;
          const hidden = document.querySelector(hiddenSelector);
          const input = document.querySelector(visibleSelector);

          if (hidden && input) {
            hidden.value = match[target.hidden];
            input.value = match[target.input];
            console.debug(
              `[cmnsd:semantic] matched '${word}' → ${target.field}=${match[target.input]}`
            );
            const ev = new Event('input', { bubbles: true });
            input.dispatchEvent(ev);
            highlight(input, '#d1e7dd'); // ✅ green flash
          }
        }
      }
    }
  }

  const debouncedAnalyze = debounce(analyzeAndFill, 600);

  document.addEventListener('input', e => {
    const el = e.target;
    // Trigger only for location-like fields
    if (!el.matches('[data-autosuggest][data-url*="location"]')) return;
    debouncedAnalyze(el);
  });

  console.debug('[cmnsd:semantic] initialized with targets', targets);
}