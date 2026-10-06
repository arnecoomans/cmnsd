// Pickers for cmnsd.js: search for an object and choose it, e.g. "add a
// part" (fmly: content/_parts_edit.html).
// Indentation: 2 spaces. Docs in English.
//
// A form marked data-cmnsd-picker="<model>" that is also an action form
// (data-cmnsd-action, actions.js) holds:
//   [data-picker-input]    a search box - typing (debounced, 2+ chars)
//                          GETs <apiRoot><model>/?<param>=...&format=picker
//                          (the API renders <model>/<model>_picker.html)
//   [data-picker-results]  where the results go
//   [data-picker-value]    a hidden input that receives the chosen token
// Each result is a button [data-picker-choose="<token>"]; choosing one
// submits the form - actions.js then POSTs the action. Options on the form:
//   data-picker-param="q"      the search parameter (CMNSD_SEARCH_CHARACTER)
//   data-picker-exclude="a,b"  tokens not to offer (e.g. the item itself)
//   data-picker-as="object"    the chosen token becomes the action's object
//                              (data-object-token) instead of the value -
//                              "make THIS a part of <chosen>"
//   data-picker-create="<label>"  when no result's data-picker-name equals
//                              the search exactly, offer "<label> “search”":
//                              it puts the search in [data-picker-new] (no
//                              token) and submits - the server creates it
//   data-picker-new-url + data-picker-new-param + data-picker-new-label
//                              for a model created elsewhere (more fields
//                              than a name): a link to <url>?<param>=<search>,
//                              in a new tab - also with an exact match (a
//                              namesake), after the results
//   data-picker-new-dialog="<api create url>" (with -new-param, -new-label)
//                              instead: "+ new" opens that form in a dialog
//                              (dialog.js, cmnsd object_create), prefilled
//                              with ?<param>=<search>; once saved, the new
//                              object is chosen like a search result
// After a choice the search and results clear and the chosen token is
// excluded from then on, so adding several in a row is quick.
//
// A field picker - an element (not a form) marked data-cmnsd-picker inside
// another form, rendered by cmnsd.forms.widgets.PickerInput - chooses one
// object for a form field (e.g. a place's parent): the chosen token goes
// into its [data-picker-value] (the field's hidden input) and its name
// into [data-picker-chosen]. With data-picker-submit the surrounding form
// is submitted (an edit block saves); [data-picker-clear] empties the
// field the same way.
// Keys: Enter chooses the first result, ArrowDown moves into the results,
// Escape clears. Without JS the picker isn't rendered usable: it's an
// edit-mode control, and edit mode's fallback is the admin.

import { apiUrl, latest, request } from './api.js';
import { closest, once } from './dom.js';
import { createDialog } from './dialog.js';
import { config, dbg } from './context.js';

const SELECTOR = '[data-cmnsd-picker]';
const DELAY = 250;
const MIN_CHARS = 2;

function bindPicker(picker) {
  if (!once(picker, 'picker')) return;
  // The picker is the action form itself, or a field inside another form.
  const isForm = picker.matches('form');
  const form = isForm ? picker : picker.closest('form');
  const input = picker.querySelector('[data-picker-input]');
  const results = picker.querySelector('[data-picker-results]');
  const value = picker.querySelector('[data-picker-value]');
  const chosen = picker.querySelector('[data-picker-chosen]');
  if (!input || !results) return;
  const exclude = new Set((picker.dataset.pickerExclude || '').split(',').filter(Boolean));
  // Only the latest search counts (api.js latest: waits DELAY, aborts the one before).
  const search = latest(async (signal) => {
    const query = input.value.trim();
    if (query.length < MIN_CHARS) {
      results.innerHTML = '';
      return;
    }
    const url = apiUrl(config.apiRoot, [picker.dataset.cmnsdPicker], { [picker.dataset.pickerParam || 'q']: query, format: 'picker' });
    dbg('picker GET', url);
    try {
      const { data } = await request(url, { signal });
      results.innerHTML = data.html || '';
      results.querySelectorAll('[data-picker-choose]').forEach((button) => {
        if (exclude.has(button.dataset.pickerChoose)) (button.closest('[data-picker-row]') || button).remove();
      });
      offerCreate(query);
    } catch (err) {
      if (err.name !== 'AbortError') dbg('picker failed', url, err);
    }
  }, DELAY);

  const fresh = picker.querySelector('[data-picker-new]');

  function offerCreate(query) {
    const create = picker.hasAttribute('data-picker-create');
    const newUrl = picker.dataset.pickerNewUrl;
    const newDialog = picker.dataset.pickerNewDialog;
    if (!create && !newUrl && !newDialog) return;
    const wanted = query.toLocaleLowerCase();
    const exact = [...results.querySelectorAll('[data-picker-name]')]
      .some((el) => el.dataset.pickerName.toLocaleLowerCase() === wanted);
    // An exact match: no instant create (a second "Bake" tag). A form (new
    // url / dialog) is still offered - a namesake is real (a father and son
    // both "Jan Schriek"), and the form has room for its own checks.
    if (create && !exact) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'picker-result picker-result--create';
      button.dataset.pickerCreateName = query;
      button.textContent = `${picker.dataset.pickerCreate || '+'} “${query}”`;
      results.append(button);
    }
    if (newDialog) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'picker-result picker-result--create';
      button.dataset.pickerNewDialog = query;
      button.textContent = `${picker.dataset.pickerNewLabel || '+'} “${query}”`;
      results.append(button);
    } else if (newUrl) {
      const link = document.createElement('a');
      const url = new URL(newUrl, window.location.href);
      if (picker.dataset.pickerNewParam) url.searchParams.set(picker.dataset.pickerNewParam, query);
      link.href = url;
      link.target = '_blank';
      link.rel = 'noopener';
      link.className = 'picker-result picker-result--create';
      link.dataset.pickerNewLink = '';
      link.textContent = `${picker.dataset.pickerNewLabel || '+'} “${query}” ↗`;
      results.append(link);
    }
  }

  function submit() {
    // An action form always submits; a field picker only when asked to
    // (data-picker-submit) - else the choice waits for the form's own Save.
    if (form && (isForm || picker.hasAttribute('data-picker-submit'))) form.requestSubmit();
    search.cancel();   // a search still in flight must not fill the results again
    input.value = '';
    results.innerHTML = '';
  }

  function choose(button) {
    if (!button || button.disabled) return;
    if (button.hasAttribute('data-picker-new-link')) {
      window.open(button.href, '_blank', 'noopener');
      return;
    }
    if (button.dataset.pickerNewDialog !== undefined) {
      // "+ new": the form in a dialog; once saved, choose what was made.
      const url = new URL(picker.dataset.pickerNewDialog, window.location.href);
      if (picker.dataset.pickerNewParam) url.searchParams.set(picker.dataset.pickerNewParam, button.dataset.pickerNewDialog);
      const label = (picker.dataset.pickerNewLabel || '').replace(/^\+\s*/, '');
      createDialog(url.toString(), { title: label }).then((created) => {
        if (!created) {
          input.focus();
          return;
        }
        const token = created.token;
        if (isForm && picker.dataset.pickerAs === 'object') picker.dataset.objectToken = token;
        else if (value) value.value = token;
        if (chosen) chosen.textContent = created.name;
        if (fresh) fresh.value = '';
        exclude.add(token);
        submit();
      });
      return;
    }
    if (button.dataset.pickerCreateName) {
      if (value) value.value = '';
      if (fresh) fresh.value = button.dataset.pickerCreateName;
      if (chosen) chosen.textContent = `${button.dataset.pickerCreateName} (+)`;   // a field picker: made on save
      dbg('picker create', button.dataset.pickerCreateName);
      submit();
      return;
    }
    const token = button.dataset.pickerChoose;
    if (isForm && picker.dataset.pickerAs === 'object') picker.dataset.objectToken = token;
    else if (value) value.value = token;
    if (chosen) chosen.textContent = button.dataset.pickerName || token;
    if (fresh) fresh.value = '';
    exclude.add(token);
    dbg('picker chose', token);
    submit();
  }

  input.addEventListener('input', () => search());
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      // Never submit without a choice; Enter takes the first result.
      event.preventDefault();
      choose(results.querySelector('[data-picker-choose]:not([disabled]), [data-picker-create-name], [data-picker-new-link], [data-picker-new-dialog]'));
    } else if (event.key === 'ArrowDown') {
      event.preventDefault();
      results.querySelector('[data-picker-choose]:not([disabled]), [data-picker-create-name], [data-picker-new-link], [data-picker-new-dialog]')?.focus();
    } else if (event.key === 'Escape') {
      // Esc first clears the search; only an empty search lets it through
      // (e.g. to cancel the edit block around a field picker).
      if (input.value) event.stopPropagation();
      search.cancel();
      input.value = '';
      results.innerHTML = '';
    }
  });
  picker.querySelector('[data-picker-clear]')?.addEventListener('click', (event) => {
    event.preventDefault();
    if (value) value.value = '';
    if (fresh) fresh.value = '';
    if (chosen) chosen.textContent = '';
    submit();
  });
  results.addEventListener('click', (event) => {
    const button = closest(event, '[data-picker-choose], [data-picker-create-name], [data-picker-new-dialog]');
    if (!button) return;
    event.preventDefault();
    choose(button);
  });
  results.addEventListener('keydown', (event) => {
    const buttons = [...results.querySelectorAll('[data-picker-choose]:not([disabled]), [data-picker-create-name], [data-picker-new-link], [data-picker-new-dialog]')];
    const index = buttons.indexOf(document.activeElement);
    if (event.key === 'ArrowDown' && index < buttons.length - 1) { event.preventDefault(); buttons[index + 1].focus(); }
    if (event.key === 'ArrowUp') { event.preventDefault(); (index > 0 ? buttons[index - 1] : input).focus(); }
    if (event.key === 'Escape') input.focus();
  });
}

export function bindPickers(root) {
  root.querySelectorAll(SELECTOR).forEach((picker) => bindPicker(picker));
}
