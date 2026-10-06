// Autosave for cmnsd.js forms.
// Indentation: 2 spaces. Docs in English.
//
// A form marked data-cmnsd-autosave (posting to a cmnsd block or child
// endpoint, with the hidden _modified field) saves itself:
// - a moment after typing stops (DELAY), when a field loses focus, and on
//   Ctrl/Cmd+S - never while nothing changed (so an empty new form creates
//   nothing);
// - a create endpoint (cmnsd object_children) answers with `child`: the
//   form then posts to that child's own address, so it keeps saving the
//   same record; `modified` keeps the stale check current;
// - [data-autosave-status] shows the state - its data-text-saving /
//   -saved / -unsaved / -error give the words; an error (a validation
//   message, or 409 - changed by someone else, which stops autosaving
//   until a reload) also goes into the form's [data-cmnsd-error];
// - leaving the page with unsaved changes gets the browser's warning.
// After each save the form fires `cmnsd:autosaved` (detail: the response),
// e.g. for the page to update a tab's label.
//
// A close button - [data-autosave-close="<form id>"], a link anywhere on
// the page - is only usable while everything is saved: disabled (and its
// click ignored) from the first change until the save completes, so
// leaving through it never loses text.

import { request } from './api.js';
import { once } from './dom.js';
import { clearError, showError } from './messages.js';

const SELECTOR = 'form[data-cmnsd-autosave]';
const DELAY = 1200;

function serialize(form) {
  const data = new FormData(form);
  data.delete('_modified');
  return new URLSearchParams(data).toString();
}

function validationText(data) {
  const fields = data.errors?.validation || {};
  const texts = Object.values(fields).flat().map((error) => error.message || error).filter(Boolean);
  return texts.length ? texts.join(' ') : data.error;
}

function bindAutosave(form) {
  if (!once(form, 'autosave')) return;
  const status = form.querySelector('[data-autosave-status]');
  let saved = serialize(form);
  let timer = null;
  let saving = false;
  let again = false;
  let stopped = false;

  const closers = form.id ? [...document.querySelectorAll(`[data-autosave-close="${form.id}"]`)] : [];
  closers.forEach((closer) => closer.addEventListener('click', (event) => {
    if (closer.getAttribute('aria-disabled') === 'true') event.preventDefault();
  }));
  const say = (state, text) => {
    // Closing is safe only when nothing is waiting to be saved.
    const safe = state === 'saved' || state === 'new';
    closers.forEach((closer) => {
      closer.setAttribute('aria-disabled', safe ? 'false' : 'true');
      closer.classList.toggle('is-disabled', !safe);
    });
    if (!status) return;
    status.dataset.state = state;
    // text '' means: show nothing (a new, untouched form) - not the state's name.
    status.textContent = text ?? (status.dataset[`text${state.charAt(0).toUpperCase()}${state.slice(1)}`] || state);
  };
  const changed = () => serialize(form) !== saved;

  async function save() {
    clearTimeout(timer);
    if (stopped || !changed()) return;
    if (saving) {
      again = true;
      return;
    }
    saving = true;
    const sent = serialize(form);
    say('saving');
    try {
      const { ok, status: code, data } = await request(form.action, { method: 'POST', form: new FormData(form), messages: 'none' });
      if (ok) {
        saved = sent;
        const modified = form.querySelector('input[name="_modified"]');
        if (modified && data.modified !== undefined) modified.value = data.modified;
        if (data.child?.edit) form.action = data.child.edit;
        clearError(form);
        say(changed() ? 'unsaved' : 'saved');
        form.dispatchEvent(new CustomEvent('cmnsd:autosaved', { detail: data, bubbles: true }));
      } else {
        if (code === 409) stopped = true;
        const text = code === 400 ? validationText(data) : data.error;
        showError(form, text);
        say('error');
      }
    } catch (err) {
      showError(form, err.message);
      say('error');
    } finally {
      saving = false;
      if (again) {
        again = false;
        save();
      }
    }
  }

  form.addEventListener('input', () => {
    if (stopped) return;
    say(changed() ? 'unsaved' : 'saved');
    clearTimeout(timer);
    timer = setTimeout(save, DELAY);
  });
  form.addEventListener('change', () => save());
  form.addEventListener('focusout', () => save());
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    save();
  });
  form.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
      event.preventDefault();
      save();
    }
  });
  window.addEventListener('beforeunload', (event) => {
    if (!form.isConnected || (!changed() && !saving)) return;
    event.preventDefault();
    event.returnValue = '';
  });
  // A new record (data-cmnsd-autosave="new") starts without a status; an
  // existing one as saved.
  if (form.dataset.cmnsdAutosave === 'new') say('new', '');
  else say('saved');
}

export function bindAutosaves(root) {
  root.querySelectorAll(SELECTOR).forEach(bindAutosave);
}
