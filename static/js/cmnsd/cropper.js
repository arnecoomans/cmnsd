// static/js/cmnsd/cropper.js
// Simple cmnsd.js cropper module
// Indentation: 2 spaces

function parseFieldMap(str) {
  // "x=portrait_x,y=portrait_y,w=portrait_w,h=portrait_h"
  const map = { x: 'x', y: 'y', w: 'w', h: 'h' };
  if (!str) return map;
  str.split(',').forEach(part => {
    const [k, v] = part.split('=').map(s => s.trim());
    if (k && v && map.hasOwnProperty(k)) map[k] = v;
  });
  return map;
}

function initSingleCropper(container) {
  if (container.dataset.cropperBound === '1') return;
  container.dataset.cropperBound = '1';

  const targetSelector = container.dataset.cropperTarget || 'img';
  const saveSelector = container.dataset.cropperSave || null;
  const fieldMapStr = container.dataset.cropperFields || 'x=x,y=y,w=w,h=h';

  const img = container.querySelector(targetSelector);
  const rect =
    container.querySelector('.cmnsd-crop-rect') ||
    container.querySelector('#crop-rect') ||
    (() => {
      const r = document.createElement('div');
      r.className = 'cmnsd-crop-rect';
      container.appendChild(r);
      return r;
    })();

  if (!img) {
    console.warn('[cmnsd:cropper] no image found in', container);
    return;
  }

  let saveBtn = saveSelector ? document.querySelector(saveSelector) : null;
  if (!saveBtn) {
    console.warn('[cmnsd:cropper] no save button found for', container);
  }

  // If inside a form[data-action], that's the real action element
  const parentForm = container.closest('form[data-action]');
  const actionEl = parentForm || saveBtn;

  const fieldMap = parseFieldMap(fieldMapStr);

  let naturalW = 0;
  let naturalH = 0;

  function ensureNaturalSize() {
    if (img.naturalWidth && img.naturalHeight) {
      naturalW = img.naturalWidth;
      naturalH = img.naturalHeight;
      return;
    }
    const tmp = new Image();
    tmp.onload = () => {
      naturalW = tmp.naturalWidth;
      naturalH = tmp.naturalHeight;
      console.debug('[cmnsd:cropper] natural size (fallback)', naturalW, naturalH);
    };
    tmp.src = img.currentSrc || img.src;
  }

  if (img.complete) {
    ensureNaturalSize();
  } else {
    img.addEventListener('load', ensureNaturalSize);
  }

  let dragging = false;
  let startX = 0;
  let startY = 0;

  container.addEventListener('mousedown', e => {
    const box = container.getBoundingClientRect();

    dragging = true;
    startX = e.clientX - box.left;
    startY = e.clientY - box.top;

    rect.style.left = `${startX}px`;
    rect.style.top = `${startY}px`;
    rect.style.width = '0px';
    rect.style.height = '0px';
    rect.style.display = 'block';

    console.debug('[cmnsd:cropper] mousedown', { startX, startY });
  });

  document.addEventListener('mousemove', e => {
    if (!dragging) return;
    const box = container.getBoundingClientRect();
    const currentX = e.clientX - box.left;
    const currentY = e.clientY - box.top;

    const x = Math.min(startX, currentX);
    const y = Math.min(startY, currentY);
    const w = Math.abs(currentX - startX);
    const h = Math.abs(currentY - startY);

    rect.style.left = `${x}px`;
    rect.style.top = `${y}px`;
    rect.style.width = `${w}px`;
    rect.style.height = `${h}px`;
  });

  document.addEventListener('mouseup', () => {
    if (!dragging) return;
    dragging = false;

    if (!naturalW || !naturalH) {
      console.warn('[cmnsd:cropper] natural image size unknown; aborting crop');
      rect.style.display = 'none';
      return;
    }

    const box = container.getBoundingClientRect();
    const dispX = parseFloat(rect.style.left) || 0;
    const dispY = parseFloat(rect.style.top) || 0;
    const dispW = parseFloat(rect.style.width) || 0;
    const dispH = parseFloat(rect.style.height) || 0;

    if (dispW <= 0 || dispH <= 0) {
      console.debug('[cmnsd:cropper] zero-size crop; ignoring');
      rect.style.display = 'none';
      return;
    }

    const scaleX = naturalW / box.width;
    const scaleY = naturalH / box.height;

    const nx = Math.round(dispX * scaleX);
    const ny = Math.round(dispY * scaleY);
    const nw = Math.round(dispW * scaleX);
    const nh = Math.round(dispH * scaleY);

    const payload = {};
    payload[fieldMap.x] = nx;
    payload[fieldMap.y] = ny;
    payload[fieldMap.w] = nw;
    payload[fieldMap.h] = nh;

    console.debug('[cmnsd:cropper] crop payload', payload);

    if (actionEl) {
      actionEl.dataset.body = JSON.stringify(payload);
      console.debug('[cmnsd:cropper] attached payload to', actionEl);
    }

    if (saveBtn) {
      saveBtn.disabled = false;
    }

    container.dispatchEvent(
      new CustomEvent('cmnsd:cropper:changed', {
        bubbles: true,
        detail: { payload, container, image: img }
      })
    );
  });
}

export function initCropper(root = document) {
  const scope = root || document;
  const nodes = scope.querySelectorAll('[data-cropper]');
  nodes.forEach(node => {
    try {
      initSingleCropper(node);
    } catch (err) {
      console.error('[cmnsd:cropper] init failed for', node, err);
    }
  });
}