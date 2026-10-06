// Uploading files for cmnsd.js: a dropzone.
// Indentation: 2 spaces. Docs in English.
//
// A container marked data-cmnsd-upload="<url>" holds a file input
// ([data-upload-input], multiple) and a list ([data-upload-list]); the
// container itself is the drop area. Files - dropped or chosen - are sent
// one at a time - sorted by name, numbers as numbers - each as its own POST (multipart, field `file`, with the
// CSRF token) to <url>, with a progress bar per file: a large scan doesn't
// hold up the rest, and one failure stops nothing else. Each row shows
// the answer (the cmnsd API shape): `created` {name, url, thumb} - a link
// to the new item; `duplicate` {name, url, deleted} - already in the
// archive; or the error. When the queue is done, [data-upload-done] (if
// any) is shown. data-upload-count="<selector>" on the container: that
// element's number goes up with every file added (e.g. an inbox count).
// data-upload-thumbs="<selector>": each added file goes at the front of
// that element as a link to it (its thumbnail, else its name) - a strip of
// the latest, kept at data-upload-thumbs-max (if set) - so it shows
// without a reload. XMLHttpRequest, not fetch: it reports upload progress.

import { csrfToken } from './csrf.js';
import { once } from './dom.js';

const SELECTOR = '[data-cmnsd-upload]';

function row(list, file) {
  const item = document.createElement('li');
  item.className = 'upload-row';
  item.innerHTML = '<span class="upload-row__thumb"></span><span class="upload-row__name"></span>'
    + '<span class="upload-row__status"></span><progress class="upload-row__progress" max="100" value="0"></progress>';
  item.querySelector('.upload-row__name').textContent = file.name;
  list.append(item);
  return item;
}

function link(url, text) {
  const a = document.createElement('a');
  a.href = url;
  a.textContent = text;
  return a;
}

function send(url, file, item, labels) {
  return new Promise((resolve) => {
    const status = item.querySelector('.upload-row__status');
    const progress = item.querySelector('.upload-row__progress');
    const xhr = new XMLHttpRequest();
    xhr.open('POST', url);
    xhr.setRequestHeader('X-CSRFToken', csrfToken());
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.setRequestHeader('Accept', 'application/json');
    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable) progress.value = Math.round((event.loaded / event.total) * 100);
    });
    status.textContent = labels.sending;
    xhr.addEventListener('loadend', () => {
      progress.remove();
      let data = {};
      try { data = JSON.parse(xhr.responseText); } catch (err) { data = {}; }
      status.textContent = '';
      if (xhr.status === 200 && data.created) {
        item.classList.add('is-done');
        labels.onAdded?.(data.created);
        if (data.created.thumb) item.querySelector('.upload-row__thumb').innerHTML = `<img src="${data.created.thumb}" alt="">`;
        status.append(link(data.created.url, labels.added));
      } else if (xhr.status === 200 && data.duplicate) {
        item.classList.add('is-duplicate');
        status.textContent = data.duplicate.deleted ? labels.duplicateDeleted : labels.duplicate;
        if (data.duplicate.url) { status.append(' '); status.append(link(data.duplicate.url, data.duplicate.name)); }
      } else {
        item.classList.add('is-error');
        status.textContent = data.error || (xhr.status === 413 ? labels.tooLarge : `${labels.failed} (HTTP ${xhr.status || '-'})`);
      }
      resolve();
    });
    const body = new FormData();
    body.append('file', file);
    xhr.send(body);
  });
}

function bindUpload(zone) {
  if (!once(zone, 'upload')) return;
  const input = zone.querySelector('[data-upload-input]');
  const list = zone.querySelector('[data-upload-list]');
  const done = zone.parentElement.querySelector('[data-upload-done]');
  const labels = {
    sending: zone.dataset.textSending || 'Sending…',
    added: zone.dataset.textAdded || 'Added - open',
    duplicate: zone.dataset.textDuplicate || 'Already in the archive:',
    duplicateDeleted: zone.dataset.textDuplicateDeleted || 'Already in the archive (deleted - restore it in the admin).',
    tooLarge: zone.dataset.textTooLarge || 'Too large for the server.',
    failed: zone.dataset.textFailed || 'Not added',
    onAdded: (created) => {
      const counter = zone.dataset.uploadCount && document.querySelector(zone.dataset.uploadCount);
      if (counter) counter.textContent = String((parseInt(counter.textContent, 10) || 0) + 1);
      const strip = zone.dataset.uploadThumbs && document.querySelector(zone.dataset.uploadThumbs);
      if (strip && created) {
        const a = link(created.url, '');
        a.title = created.name || '';
        if (created.thumb) {
          const img = document.createElement('img');
          img.src = created.thumb;
          img.alt = created.name || '';
          a.append(img);
        } else {
          a.textContent = created.name || '…';
        }
        strip.prepend(a);
        strip.hidden = false;
        const max = parseInt(zone.dataset.uploadThumbsMax, 10);
        while (max && strip.children.length > max) strip.lastElementChild.remove();
      }
    },
  };
  let queue = Promise.resolve();
  const add = (files) => {
    // By name, numbers as numbers ("page 2" before "page 10"): the order a
    // scanner or camera gave them - a browser's drop or selection order
    // isn't (it can come reversed).
    const byName = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' });
    [...files].sort((a, b) => byName.compare(a.name, b.name)).forEach((file) => {
      const item = row(list, file);
      queue = queue.then(() => send(zone.dataset.cmnsdUpload, file, item, labels));
    });
    queue = queue.then(() => { if (done) done.hidden = false; });
  };
  input?.addEventListener('change', () => { add(input.files); input.value = ''; });
  ['dragenter', 'dragover'].forEach((type) => zone.addEventListener(type, (event) => {
    event.preventDefault();
    zone.classList.add('is-over');
  }));
  ['dragleave', 'drop'].forEach((type) => zone.addEventListener(type, () => zone.classList.remove('is-over')));
  zone.addEventListener('drop', (event) => {
    event.preventDefault();
    if (event.dataTransfer?.files?.length) add(event.dataTransfer.files);
  });
}

export function bindUploads(root) {
  root.querySelectorAll(SELECTOR).forEach(bindUpload);
}
