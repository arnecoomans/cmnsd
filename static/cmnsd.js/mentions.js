// Mentions while typing for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// A textarea marked data-cmnsd-mentions="person:People,event:Events,..."
// (the {% mentions_attrs %} tag, or cmnsd.forms.widgets.MentionTextarea:
// the API names in CMNSD_MENTION_MODELS, with their own translated names)
// offers what to mention as you type: "@" at the start of a word, then at
// least MIN_CHARS letters, searches each kind through the API's picker
// format (api/<model>/?q=...&format=picker - only what this writer may see)
// and lists them under the field, grouped by kind. Enter, Tab or a click
// puts [Name](kind:<token>) in place of "@..." (cmnsd/markdown/mentions.py
// renders it); arrows move, Escape closes. The text then fires `input`, so
// an edit block or autosave notices the change. data-cmnsd-mentions-param:
// the API's search parameter (CMNSD_SEARCH_CHARACTER, default q).
//
// Several words: every word must match (the API's search), so a search
// that found nothing won't find more with words added - it stops there,
// no more requests, and the list stays closed. Escape is final for that
// "@": typing on doesn't open it again. A token (from an address) after
// "@" finds that object.
//
// Your own words as the label: "[the mother of their children](@" and a
// search fills in only the destination - "person:<token>)" - and the
// words stay. No second ")" when one follows already.

import { apiUrl, latest, request } from './api.js';
import { config, dbg } from './context.js';
import { once } from './dom.js';

const SELECTOR = 'textarea[data-cmnsd-mentions]';
const MIN_CHARS = 2;
const PER_KIND = 4;
const DELAY = 250;
// "@" at the start of the text or after a space or "(", then the search:
// at least MIN_CHARS to start, words with spaces after that ("@eric
// coomans") - not across a line, another "@" or brackets.
const TRIGGER = new RegExp(`(^|[\\s(])@([^\\s@\\[\\]()][^\\n@\\[\\]()]{${MIN_CHARS - 1},60})$`);

function kinds(textarea) {
  return textarea.dataset.cmnsdMentions.split(',').filter(Boolean).map((part) => {
    const [name, ...label] = part.split(':');
    return { name, label: label.join(':') || name };
  });
}

// A label can't hold brackets unescaped: they'd end the link.
export function escapeLabel(text) {
  return text.replace(/([[\]\\])/g, '\\$1');
}

// mentionAt(text, caret) - the "@..." ending at the caret: {start, query,
// destination}, start being where the "@" is, destination true when it's a
// link's address after "](" (your own label before it) - or null.
export function mentionAt(text, caret) {
  const match = TRIGGER.exec(text.slice(0, caret));
  if (!match) return null;
  const start = caret - match[2].length - 1;
  return { start, query: match[2], destination: text.slice(0, start).endsWith('](') };
}

// mentionText(found, name, kind, token, after) - what replaces "@...": the
// whole mention, or after "](" only the destination - its ")" unless the
// text after the caret starts with one.
export function mentionText(found, name, kind, token, after = '') {
  if (found.destination) return `${kind}:${token}${after.startsWith(')') ? '' : ')'}`;
  return `[${escapeLabel(name)}](${kind}:${token})`;
}

function bindMentions(textarea) {
  if (!once(textarea, 'mentions')) return;
  const param = textarea.dataset.cmnsdMentionsParam || 'q';
  const box = document.createElement('div');
  box.className = 'mention-results';
  box.hidden = true;
  textarea.insertAdjacentElement('afterend', box);
  let current = null;   // {start, query}: where the "@" is, and what follows it
  let options = [];
  let active = -1;
  let fruitless = null;   // {start, query}: the search here that found nothing
  let dismissed = null;   // the start of an "@" closed with Escape

  const close = () => {
    box.hidden = true;
    box.innerHTML = '';
    options = [];
    active = -1;
    current = null;
  };

  const highlight = (index) => {
    options.forEach((option, i) => option.classList.toggle('is-active', i === index));
    active = index;
    options[index]?.scrollIntoView({ block: 'nearest' });
  };

  const insert = (option) => {
    if (!current) return;
    const caret = textarea.selectionStart;
    const before = textarea.value.slice(0, current.start);
    const after = textarea.value.slice(caret);
    const mention = mentionText(current, option.dataset.pickerName || '', option.dataset.mentionKind, option.dataset.pickerChoose, after);
    textarea.value = before + mention + after;
    // After a destination that had its ")" already: past it.
    const end = before.length + mention.length + (current.destination && after.startsWith(')') ? 1 : 0);
    textarea.setSelectionRange(end, end);
    close();
    textarea.focus();
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
  };

  // The "@..." right before the caret, if the caret is at the end of one.
  const trigger = () => (textarea.selectionStart === textarea.selectionEnd ? mentionAt(textarea.value, textarea.selectionStart) : null);

  const render = (groups) => {
    box.innerHTML = '';
    options = [];
    groups.forEach(({ kind, html }) => {
      const found = document.createElement('template');
      found.innerHTML = html;
      const buttons = [...found.content.querySelectorAll('[data-picker-choose]')].slice(0, PER_KIND);
      if (!buttons.length) return;
      const group = document.createElement('div');
      group.className = 'mention-results__group';
      const heading = document.createElement('p');
      heading.className = 'mention-results__kind';
      heading.textContent = kind.label;
      group.append(heading);
      buttons.forEach((button) => {
        button.type = 'button';
        button.tabIndex = -1;
        button.dataset.mentionKind = kind.name;
        // mousedown, not click: the textarea keeps its focus and caret.
        button.addEventListener('mousedown', (event) => {
          event.preventDefault();
          insert(button);
        });
        group.append(button);
        options.push(button);
      });
      box.append(group);
    });
    if (!options.length) {
      close();
      return;
    }
    box.hidden = false;
    highlight(0);
  };

  const search = latest(async (signal) => {
    const found = trigger();
    // No "@" here; one closed with Escape; or more words after a search that
    // found nothing (each word narrows - there's nothing more to find).
    const hopeless = fruitless && found && found.start === fruitless.start && found.query.startsWith(fruitless.query);
    if (!found || found.start === dismissed || hopeless) {
      close();
      return;
    }
    current = found;
    const groups = await Promise.all(kinds(textarea).map(async (kind) => {
      const url = apiUrl(config.apiRoot, [kind.name], { [param]: found.query, format: 'picker' });
      try {
        const { data } = await request(url, { signal, messages: 'none' });
        return { kind, html: data.html || '' };
      } catch (err) {
        if (err.name === 'AbortError') throw err;
        dbg('mentions: search failed', kind.name, err);
        return { kind, html: '' };
      }
    }));
    if (current !== found) return;   // typed on since
    render(groups);
    fruitless = options.length ? null : { start: found.start, query: found.query };
  }, DELAY);

  textarea.addEventListener('input', () => search());
  textarea.addEventListener('keydown', (event) => {
    if (box.hidden || !options.length) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      highlight((active + 1) % options.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      highlight((active - 1 + options.length) % options.length);
    } else if (event.key === 'Enter' || event.key === 'Tab') {
      event.preventDefault();
      insert(options[active]);
    } else if (event.key === 'Escape') {
      // Only the list closes - not the dialog or edit block around it - and
      // stays closed for this "@".
      event.preventDefault();
      event.stopPropagation();
      dismissed = current?.start ?? null;
      close();
    }
  });
  textarea.addEventListener('blur', () => close());
}

export function bindMentionFields(root) {
  root.querySelectorAll(SELECTOR).forEach((textarea) => bindMentions(textarea));
}
