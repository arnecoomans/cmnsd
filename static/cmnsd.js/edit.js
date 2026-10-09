// Editable blocks for cmnsd.js (edit mode).
// Indentation: 2 spaces. Docs in English.
//
// A block [data-cmnsd-edit-block] (cmnsd/edit/block.html) with a pencil
// [data-cmnsd-edit-open data-cmnsd-edit-url]: the pencil GETs the block's
// form (cmnsd object_form) and puts it in place of the block's content.
//   Save   POSTs the form; on success the updated block replaces the old
//          one (and the address follows the object's new URL, e.g. after
//          a rename); on a validation error the form comes back with its
//          errors; anything else (409 - changed by someone else - or 403)
//          shows in the form's [data-cmnsd-error].
//   Cancel / Esc  puts the block back as it was - no request.
//   Ctrl/Cmd+Enter  saves.
//   ?open=<name>,<name> in the address opens those blocks on load.
//   A block with data-cmnsd-edit-dialog="<title>" opens its form in a
//   dialog instead (dialog.js) - for a form that needs room.
// Messages ("Saved.") go to the message area (messages.js). Event
// delegation: a block put back by a save works without rebinding.
//
// Choice blocks (cmnsd/edit/choices.html): each button submits its own
// value (the form's submitter); a button with data-cmnsd-confirm asks
// first, one with data-cmnsd-prompt asks for an answer that's posted along
// as data-cmnsd-prompt-name (dom.js asked - cancelled or empty: nothing
// saved); a select marked data-cmnsd-autosubmit saves on change. The
// response may say `redirect` (the object is gone for this viewer - e.g.
// set to deleted) or `reload` (the change reaches further - an item's
// kind); the messages are kept over that (messages.js). Before a reload,
// other open forms with changes are saved first, so nothing typed is lost.
//
// Unsaved changes - an open form whose fields differ from when it opened:
// - a form marked data-cmnsd-unsaved="<question>" (the Edit switch) asks
//   that question before it submits; no = stay;
// - anything else that leaves the page (a link, reload, closing the tab)
//   gets the browser's own warning (beforeunload - browsers only allow
//   their own wording there).

import { request } from './api.js';
import { asked, busy, closest, confirmed } from './dom.js';
import { enhance } from './enhance.js';
import { formDialog } from './dialog.js';
import { keepForReload, showError, showMessage, showMessages } from './messages.js';
import { dbg } from './context.js';

const originals = new WeakMap();
let leaving = false;   // the user already confirmed leaving - no second warning

function serialize(form) {
  const data = new FormData(form);
  data.delete('_modified');
  return new URLSearchParams(data).toString();
}

function unsavedForms() {
  return [...document.querySelectorAll('form[data-cmnsd-edit-form]')]
    .filter((form) => form.dataset.cmnsdInitial !== undefined && serialize(form) !== form.dataset.cmnsdInitial);
}

function cancel(block) {
  if (!originals.has(block)) return;
  block.innerHTML = originals.get(block);
  originals.delete(block);
  block.classList.remove('is-editing');
  block.querySelector('[data-cmnsd-edit-open]')?.focus();
}

function focusForm(block) {
  const first = block.querySelector('input:not([type=hidden]), textarea, select');
  if (first) {
    first.focus();
    if (first.setSelectionRange && typeof first.value === 'string') first.setSelectionRange(first.value.length, first.value.length);
  }
}

// A block marked data-cmnsd-edit-dialog edits in a dialog (dialog.js) -
// for a form that needs room, e.g. cropping a portrait. Saved: the block is
// replaced by the answer's html (or the page reloads / moves on).
async function openInDialog(block, button) {
  const title = block.dataset.cmnsdEditDialog || '';
  const data = await formDialog(button.dataset.cmnsdEditUrl, {
    title, messages: 'none', accept: (answer) => Boolean(answer.html || answer.redirect || answer.reload),
  });
  if (!data) return;
  if (data.redirect || data.reload) {
    keepForReload(data.messages);
    if (data.redirect) window.location.href = data.redirect;
    else window.location.reload();
    return;
  }
  const parent = block.parentElement;
  block.outerHTML = data.html;
  enhance(parent);
  // The page's other forms (choice buttons, open blocks) get the new version.
  updateModified(new URL(button.dataset.cmnsdEditUrl, window.location.href).href, data.modified);
  showMessages(data.messages);
}

async function open(button, { focus = true } = {}) {
  const block = button.closest('[data-cmnsd-edit-block]');
  if (!block || originals.has(block)) return;
  if (block.hasAttribute('data-cmnsd-edit-dialog')) {
    openInDialog(block, button);
    return;
  }
  dbg('GET', button.dataset.cmnsdEditUrl);
  const { ok, data } = await request(button.dataset.cmnsdEditUrl);
  if (!ok || !data.html) {
    showMessage(data.error || 'No form.', 'error');
    return;
  }
  originals.set(block, block.innerHTML);
  block.innerHTML = data.html;
  block.classList.add('is-editing');
  enhance(block);   // the form's own widgets - e.g. a picker (picker.js)
  const form = block.querySelector('form[data-cmnsd-edit-form]');
  if (form) form.dataset.cmnsdInitial = serialize(form);
  if (focus) focusForm(block);
}

// ?open=title,body - open those blocks' forms when the page loads (by
// data-cmnsd-edit-name, cmnsd/edit/block.html), e.g. a new note: write its
// title and text right away. The first one gets the focus. The parameter
// leaves the address afterwards, so a reload shows the page as it is.
async function openRequested() {
  const address = new URL(window.location.href);
  const names = (address.searchParams.get('open') || '').split(',').map((name) => name.trim()).filter(Boolean);
  if (!names.length) return;
  address.searchParams.delete('open');
  history.replaceState(history.state, '', address);
  const blocks = names
    .map((name) => document.querySelector(`[data-cmnsd-edit-block][data-cmnsd-edit-name="${CSS.escape(name)}"]`))
    .filter((block) => block && block.querySelector('[data-cmnsd-edit-open]'));
  for (const block of blocks) await open(block.querySelector('[data-cmnsd-edit-open]'), { focus: false });
  if (blocks.length) focusForm(blocks[0]);
}

// After a save, the object's other block forms on the page (same
// api/<model>/<token>/form/ prefix) get its new version (`modified`), so
// the next save isn't refused as stale - only someone else's change is.
function updateModified(action, modified) {
  if (!modified) return;
  const prefix = action.replace(/form\/[^/]+\/?$/, 'form/');
  document.querySelectorAll('form[data-cmnsd-edit-form]').forEach((other) => {
    if (!other.action.startsWith(prefix)) return;
    const input = other.querySelector('input[name="_modified"]');
    if (input) input.value = modified;
  });
}

async function save(form, submitter) {
  if (submitter && !confirmed(submitter)) return;
  const answer = submitter ? asked(submitter) : null;   // data-cmnsd-prompt: a question whose answer goes along
  if (answer === false) return;
  const block = form.closest('[data-cmnsd-edit-block]');
  const body = submitter ? new FormData(form, submitter) : new FormData(form);
  if (answer) body.append(answer.name, answer.value);
  try {
    await busy(form.querySelectorAll('button'), async () => {
      dbg('POST', form.action);
      // messages: 'none' - shown now, or kept over a reload / redirect, below.
      const { status, data } = await request(form.action, { method: 'POST', form: body, messages: 'none' });
      if (data.ok && data.reload) {
        // Other forms still open with changes (a title typed, then the kind
        // chosen): save them first - the reload would lose them. One that
        // can't be saved (an error) keeps the page here, with its error.
        // They get this save's new version first, or they'd be refused as
        // changed by someone else.
        updateModified(form.action, data.modified);
        for (const other of unsavedForms()) {
          if (other !== form) await save(other);
        }
        if (unsavedForms().some((other) => other !== form)) {
          showMessages(data.messages);
          return;
        }
      }
      if (data.ok && (data.redirect || data.reload)) {
        leaving = true;
        keepForReload(data.messages);
        if (data.redirect) window.location.href = data.redirect;
        else window.location.reload();
        return;
      }
      if (data.ok && data.removed) {
        // A child record removed (cmnsd object_children): its block goes.
        originals.delete(block);
        block.remove();
        showMessages(data.messages);
        return;
      }
      if (data.ok && data.html) {
        const action = form.action;
        const parent = block.parentElement;
        originals.delete(block);
        block.outerHTML = data.html;   // a created child: the child + a fresh "+ add"
        enhance(parent);               // the new HTML's own pickers, pills, ...
        updateModified(action, data.modified);
        showMessages(data.messages);
        if (data.url && data.url !== window.location.pathname) {
          history.replaceState(history.state, '', data.url + window.location.search + window.location.hash);
        }
        return;
      }
      showMessages(data.messages);
      if (status === 400 && data.html) {
        const initial = form.dataset.cmnsdInitial;
        block.innerHTML = data.html;          // the form with its errors - still unsaved
        enhance(block);
        const again = block.querySelector('form[data-cmnsd-edit-form]');
        if (again) again.dataset.cmnsdInitial = initial;
        block.querySelector('[aria-invalid], .edit-form__error')?.closest('.edit-form__field')?.querySelector('input, textarea, select')?.focus();
        return;
      }
      showError(form, data.error);
    });
  } catch (err) {
    dbg('edit: save failed', err);
    showMessage(err.message, 'error');
  }
}

export function bindEditBlocks(root) {
  openRequested();
  root.addEventListener('click', (event) => {
    const opener = closest(event, '[data-cmnsd-edit-open]');
    if (opener) {
      event.preventDefault();
      open(opener);
      return;
    }
    const cancelButton = closest(event, '[data-cmnsd-edit-cancel]');
    if (cancelButton) {
      event.preventDefault();
      cancel(cancelButton.closest('[data-cmnsd-edit-block]'));
    }
  });
  root.addEventListener('submit', (event) => {
    const leaver = closest(event, 'form[data-cmnsd-unsaved]');
    if (leaver) {
      if (unsavedForms().length && !window.confirm(leaver.dataset.cmnsdUnsaved)) {
        event.preventDefault();
        return;
      }
      leaving = true;
      return;
    }
    const form = closest(event, 'form[data-cmnsd-edit-form]');
    if (!form) return;
    event.preventDefault();
    save(form, event.submitter);
  });
  root.addEventListener('change', (event) => {
    const select = closest(event, 'select[data-cmnsd-autosubmit]');
    const form = select && select.closest('form[data-cmnsd-edit-form]');
    if (form) form.requestSubmit();
  });
  window.addEventListener('beforeunload', (event) => {
    if (leaving || !unsavedForms().length) return;
    event.preventDefault();
    event.returnValue = '';   // older browsers need it set
  });
  root.addEventListener('keydown', (event) => {
    const form = closest(event, 'form[data-cmnsd-edit-form]');
    if (!form) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      cancel(form.closest('[data-cmnsd-edit-block]'));
    } else if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
}
