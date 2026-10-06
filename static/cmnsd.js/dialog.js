// Dialogs with a form, for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
//   const data = await formDialog(url, { title, accept: (data) => ..., messages });
//   // the answer once saved (accept(data) true) - or null when closed
//   const created = await createDialog(url, { title: 'New person' });
//   // {token, name, url} - a new object (cmnsd object_create) - or null
//
// GETs the form from `url` (an API answer with `html`), shows it in a
// native <dialog> (modal: focus stays inside, Esc closes), and POSTs it on
// submit - with the button that submitted it (e.g. a "reset" button). A
// validation error (400 with `html`) puts the form back with its errors;
// an answer that accept() takes closes the dialog and resolves with it.
// Esc, the close button, Cancel ([data-cmnsd-dialog-close]) or a click
// beside the dialog close it without saving. `messages` is passed to
// api.js request() ('show' by default; 'none' when the caller decides,
// e.g. keeps them over a reload). The submit doesn't reach the page's own
// handlers (edit.js): the dialog handles its form.
// A button in it marked data-cmnsd-dialog-answer='<JSON>' answers the
// dialog with that, without posting - when accept() takes it: e.g. "use
// this one" beside a possible duplicate in a "+ new person" dialog
// ({created: {token, name, url}}), so the caller gets the existing object
// as it would a new one.
// Used by picker.js for "+ new ..." (createDialog), by edit.js for a block
// that edits in a dialog (data-cmnsd-edit-dialog - a portrait crop), and by
// buttons marked data-cmnsd-create (bindCreateButtons, below).

import { request } from './api.js';
import { enhance } from './enhance.js';
import { showError, showMessage } from './messages.js';
import { dbg } from './context.js';

function focusFirst(root) {
  root.querySelector('input:not([type=hidden]), textarea, select')?.focus();
}

export function formDialog(url, { title = '', accept = () => true, messages = 'show' } = {}) {
  return new Promise((resolve) => {
    const dialog = document.createElement('dialog');
    dialog.className = 'cmnsd-dialog';
    dialog.innerHTML = '<header class="cmnsd-dialog__header"><h2 class="cmnsd-dialog__title"></h2>'
      + '<button type="button" class="cmnsd-dialog__close" data-cmnsd-dialog-close aria-label="Close"><i class="bi bi-x-lg"></i></button></header>'
      + '<div class="cmnsd-dialog__body"></div>';
    dialog.querySelector('.cmnsd-dialog__title').textContent = title;
    const body = dialog.querySelector('.cmnsd-dialog__body');
    let result = null;

    // Resolve once: on save directly, otherwise when the dialog closes
    // (Esc, close button, Cancel, a click beside it).
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      if (dialog.open) dialog.close();
      dialog.remove();
      resolve(result);
    };
    dialog.addEventListener('close', finish);
    dialog.addEventListener('cancel', (event) => {   // Esc
      event.preventDefault();
      finish();
    });
    // A click beside the dialog lands on the dialog element itself - only
    // when it also started there: a drag inside (moving an image) that ends
    // outside doesn't close it.
    let downOnBackdrop = false;
    dialog.addEventListener('pointerdown', (event) => { downOnBackdrop = event.target === dialog; });
    dialog.addEventListener('click', (event) => {
      if ((event.target === dialog && downOnBackdrop) || event.target.closest('[data-cmnsd-dialog-close]')) {
        finish();
        return;
      }
      const answerButton = event.target.closest('[data-cmnsd-dialog-answer]');
      if (answerButton) {
        let answer = null;
        try {
          answer = JSON.parse(answerButton.dataset.cmnsdDialogAnswer);
        } catch (err) {
          dbg('dialog: bad answer', err);
          return;
        }
        if (accept(answer)) {
          result = answer;
          finish();
        }
      }
    });
    dialog.addEventListener('submit', async (event) => {
      const form = event.target.closest('form');
      if (!form) return;
      event.preventDefault();
      event.stopPropagation();   // the dialog handles its form, not the page's handlers
      const data = event.submitter ? new FormData(form, event.submitter) : new FormData(form);
      const buttons = form.querySelectorAll('button');
      buttons.forEach((button) => { button.disabled = true; });
      try {
        const { ok, status, data: answer } = await request(form.action, { method: 'POST', form: data, messages });
        if (ok && accept(answer)) {
          result = answer;
          finish();
          return;
        }
        if (status === 400 && answer.html) {
          body.innerHTML = answer.html;
          enhance(body);
          body.querySelector('[aria-invalid], .edit-form__error')?.closest('.edit-form__field')?.querySelector('input, select, textarea')?.focus();
          return;
        }
        showError(form, answer.error);
      } catch (err) {
        dbg('dialog: save failed', err);
        showError(form, err.message);
      } finally {
        buttons.forEach((button) => { button.disabled = false; });
      }
    });
    // Esc inside the form is the dialog's (cancel), not an edit block's.
    dialog.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') event.stopPropagation();
    });

    document.body.append(dialog);
    request(url).then(({ ok, data }) => {
      if (!ok || !data.html) {
        showMessage(data.error || 'No form.', 'error');
        finish();
        return;
      }
      body.innerHTML = data.html;
      dialog.showModal();   // shown before enhancing: a viewer measures its frame
      enhance(body);
      focusFirst(body);
    }).catch((err) => {
      dbg('dialog: load failed', err);
      showMessage(err.message, 'error');
      finish();
    });
  });
}

// A new object (cmnsd object_create): resolves with its {token, name, url}.
export function createDialog(url, { title = '', messages = 'show' } = {}) {
  return formDialog(url, { title, messages, accept: (data) => Boolean(data.created) }).then((data) => (data ? data.created : null));
}

// A button that creates an object in a dialog - e.g. "+ New event":
//   <button data-cmnsd-create="/api/event/new/?kind=historical"
//           data-cmnsd-create-title="New event" data-cmnsd-create-then="open">
// then: "open" (default) goes to the new object's page, "reload" reloads
// this one (messages kept over it). Event delegation: works for buttons
// added later.
export function bindCreateButtons(root) {
  root.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-cmnsd-create]');
    if (!button) return;
    event.preventDefault();
    // The page changes next: "added" is kept for it (messages.js).
    const created = await createDialog(button.dataset.cmnsdCreate, { title: button.dataset.cmnsdCreateTitle || '', messages: 'keep' });
    if (!created) return;
    if ((button.dataset.cmnsdCreateThen || 'open') === 'reload' || !created.url) window.location.reload();
    else window.location.href = created.url;
  });
}
