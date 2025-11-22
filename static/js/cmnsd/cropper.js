// cmnsd/cropper.js
// Simple drag-to-crop helper for cmnsd.js (Option A)
// - Auto-binds on [data-cropper]
// - Converts displayed selection to natural pixel coords
// - Writes JSON payload to save button's data-body
// - Supports field mapping via data-cropper-fields="x=portrait_x,y=...,w=...,h=..."
// - Optional aspect lock via data-cropper-aspect="1:1" or "4:3" etc.

function parseFieldMap(str) {
  // default: x,y,w,h
  const map = { x: 'x', y: 'y', w: 'w', h: 'h' };
  if (!str) return map;
  str.split(',').forEach(pair => {
    const [from, to] = pair.split('=').map(s => s.trim());
    if (from && to) map[from] = to;
  });
  return map;
}

function parseAspect(str) {
  if (!str) return null;
  const trimmed = String(str).trim();
  if (!trimmed) return null;

  // "4:3" or "1:1"
  if (trimmed.includes(':')) {
    const [a, b] = trimmed.split(':').map(parseFloat);
    if (a > 0 && b > 0) {
      return a / b; // width / height
    }
    return null;
  }

  const val = parseFloat(trimmed);
  return val > 0 ? val : null;
}

function setupCropper(wrapper) {
  if (wrapper.dataset.cropperBound === '1') return;
  wrapper.dataset.cropperBound = '1';

  const targetSel = wrapper.dataset.cropperTarget || 'img';
  const img = wrapper.querySelector(targetSel);
  if (!img) {
    console.warn('[cmnsd:cropper] no target image found for', wrapper);
    return;
  }

  // Ensure wrapper style is usable
  const cs = getComputedStyle(wrapper);
  if (cs.position === 'static') {
    wrapper.style.position = 'relative';
  }
  wrapper.style.userSelect = 'none';
  wrapper.style.touchAction = 'none'; // iOS helper

  // ---------------------------
  // Find / create selection rect
  // ---------------------------
  let rect = wrapper.querySelector('.cmnsd-crop-rect');
  if (!rect) {
    rect = document.createElement('div');
    rect.className = 'cmnsd-crop-rect';
    wrapper.appendChild(rect);
  }
  rect.style.display = 'none';

  // Create handles (8: corners + edges)
  const handlePositions = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'];
  const handles = {};

  handlePositions.forEach(pos => {
    let h = rect.querySelector(`.cmnsd-crop-handle--${pos}`);
    if (!h) {
      h = document.createElement('div');
      h.className = `cmnsd-crop-handle cmnsd-crop-handle--${pos}`;
      h.dataset.handle = pos;
      rect.appendChild(h);
    }
    handles[pos] = h;
  });

  // ---------------------------
  // Resolve save button
  // ---------------------------
  let saveBtn = null;
  if (wrapper.dataset.cropperSave) {
    saveBtn = document.querySelector(wrapper.dataset.cropperSave);
  }
  if (!saveBtn) {
    // Try next sibling as a fallback
    const sib = wrapper.nextElementSibling;
    if (sib && sib.matches && sib.matches('[data-action]')) {
      saveBtn = sib;
    }
  }
  if (!saveBtn) {
    console.warn('[cmnsd:cropper] no save button found for', wrapper);
  }

  // ---------------------------
  // Config
  // ---------------------------
  const fieldMap = parseFieldMap(wrapper.dataset.cropperFields);
  const aspectRatio = parseAspect(wrapper.dataset.cropperAspect);

  let naturalW = 0;
  let naturalH = 0;

  function ensureNaturalSize() {
    if (naturalW && naturalH) return;
    if (img.naturalWidth && img.naturalHeight) {
      naturalW = img.naturalWidth;
      naturalH = img.naturalHeight;
    }
  }

  // ---------------------------
  // State
  // ---------------------------
  let mode = null; // 'new' | 'move' | 'resize'
  let resizeHandle = null;
  let dragging = false;

  // crop rect in DISPLAYED image coords (relative to imgRect)
  let crop = { x: 0, y: 0, w: 0, h: 0 };

  // For dragging / moving
  let startX = 0;
  let startY = 0;
  let startCrop = null; // {x,y,w,h}
  let moveOffsetX = 0;
  let moveOffsetY = 0;

  // ---------------------------
  // Helpers
  // ---------------------------
  function hitTestRect(clientX, clientY) {
    const imgRect = img.getBoundingClientRect();
    const x = crop.x + imgRect.left;
    const y = crop.y + imgRect.top;
    const w = crop.w;
    const h = crop.h;
    return (
      clientX >= x &&
      clientX <= x + w &&
      clientY >= y &&
      clientY <= y + h
    );
  }

  function pointerInHandle(target) {
    const h = target.closest('.cmnsd-crop-handle');
    if (!h || !rect.contains(h)) return null;
    return h.dataset.handle || null;
  }

  function renderRect() {
    if (!crop.w || !crop.h) {
      rect.style.display = 'none';
      return;
    }
    const imgRect = img.getBoundingClientRect();
    const wrapperRect = wrapper.getBoundingClientRect();

    const offsetLeft = imgRect.left - wrapperRect.left;
    const offsetTop = imgRect.top - wrapperRect.top;

    rect.style.display = 'block';
    rect.style.left = `${offsetLeft + crop.x}px`;
    rect.style.top = `${offsetTop + crop.y}px`;
    rect.style.width = `${crop.w}px`;
    rect.style.height = `${crop.h}px`;

    // Handles are positioned via CSS, we don't need per-frame math
  }

  function clampCropToImage() {
    const imgRect = img.getBoundingClientRect();
    if (!imgRect.width || !imgRect.height) return;

    crop.w = Math.max(0, Math.min(crop.w, imgRect.width));
    crop.h = Math.max(0, Math.min(crop.h, imgRect.height));

    crop.x = Math.max(0, Math.min(crop.x, imgRect.width - crop.w));
    crop.y = Math.max(0, Math.min(crop.y, imgRect.height - crop.h));
  }

  function applyAspectOnNewSelection(endX, endY) {
    if (!aspectRatio) return;

    const imgRect = img.getBoundingClientRect();
    const dx = endX - startX;
    const dy = endY - startY;

    let w = Math.abs(dx);
    let h = Math.abs(dy);

    if (w === 0 && h === 0) {
      crop = { x: startX, y: startY, w: 0, h: 0 };
      return;
    }

    // Adjust h based on w (simple and intuitive)
    h = w / aspectRatio;

    // Determine direction
    const signX = dx >= 0 ? 1 : -1;
    const signY = dy >= 0 ? 1 : -1;

    const x = signX > 0 ? startX : startX - w;
    const y = signY > 0 ? startY : startY - h;

    // clamp inside image
    crop = {
      x: Math.max(0, Math.min(x, imgRect.width - w)),
      y: Math.max(0, Math.min(y, imgRect.height - h)),
      w,
      h
    };
  }

  function applyAspectOnResize(handle, endX, endY) {
    if (!aspectRatio) return;

    const imgRect = img.getBoundingClientRect();
    let { x, y, w, h } = startCrop;

    const right = x + w;
    const bottom = y + h;

    let nx = x;
    let ny = y;
    let nw = w;
    let nh = h;

    if (handle === 'se' || handle === 'ne' || handle === 'sw' || handle === 'nw') {
      // Corner resizing with aspect ratio
      const anchorX = (handle === 'se' || handle === 'ne') ? x : right;
      const anchorY = (handle === 'se' || handle === 'sw') ? y : bottom;

      const dx = endX - anchorX;
      const dy = endY - anchorY;

      let absW = Math.abs(dx);
      let absH = absW / aspectRatio;

      // direction
      const signX = (handle === 'se' || handle === 'ne') ? 1 : -1;
      const signY = (handle === 'se' || handle === 'sw') ? 1 : -1;

      nw = absW;
      nh = absH;

      nx = signX > 0 ? anchorX : anchorX - nw;
      ny = signY > 0 ? anchorY : anchorY - nh;

      // clamp inside image
      nw = Math.min(nw, imgRect.width);
      nh = Math.min(nh, imgRect.height);

      nx = Math.max(0, Math.min(nx, imgRect.width - nw));
      ny = Math.max(0, Math.min(ny, imgRect.height - nh));

      crop = { x: nx, y: ny, w: nw, h: nh };
    } else {
      // Edge handles: basic free resize, aspect ignored
      applyResizeWithoutAspect(handle, endX, endY);
    }
  }

  function applyResizeWithoutAspect(handle, endX, endY) {
    const imgRect = img.getBoundingClientRect();
    let { x, y, w, h } = startCrop;

    const right = x + w;
    const bottom = y + h;

    let nx = x;
    let ny = y;
    let nw = w;
    let nh = h;

    if (handle === 'e' || handle === 'ne' || handle === 'se') {
      nw = Math.max(0, endX - x);
    }
    if (handle === 'w' || handle === 'nw' || handle === 'sw') {
      nx = Math.min(endX, right);
      nw = right - nx;
    }
    if (handle === 's' || handle === 'se' || handle === 'sw') {
      nh = Math.max(0, endY - y);
    }
    if (handle === 'n' || handle === 'ne' || handle === 'nw') {
      ny = Math.min(endY, bottom);
      nh = bottom - ny;
    }

    // clamp
    nw = Math.min(nw, imgRect.width);
    nh = Math.min(nh, imgRect.height);
    nx = Math.max(0, Math.min(nx, imgRect.width - nw));
    ny = Math.max(0, Math.min(ny, imgRect.height - nh));

    crop = { x: nx, y: ny, w: nw, h: nh };
  }

  function beginNewSelection(e) {
    ensureNaturalSize();
    if (!naturalW || !naturalH) {
      console.warn('[cmnsd:cropper] natural size unknown for image', img);
      return;
    }

    const imgRect = img.getBoundingClientRect();
    const cx = e.clientX;
    const cy = e.clientY;

    if (
      cx < imgRect.left ||
      cx > imgRect.right ||
      cy < imgRect.top ||
      cy > imgRect.bottom
    ) {
      return;
    }

    dragging = true;
    mode = 'new';

    startX = cx - imgRect.left;
    startY = cy - imgRect.top;
    startCrop = null;

    crop = { x: startX, y: startY, w: 0, h: 0 };
    renderRect();

    e.preventDefault();
  }

  function beginMove(e) {
    dragging = true;
    mode = 'move';

    const imgRect = img.getBoundingClientRect();
    const cx = e.clientX - imgRect.left;
    const cy = e.clientY - imgRect.top;

    moveOffsetX = cx - crop.x;
    moveOffsetY = cy - crop.y;

    startCrop = { ...crop };
    e.preventDefault();
  }

  function beginResize(e, handle) {
    dragging = true;
    mode = 'resize';
    resizeHandle = handle;
    startCrop = { ...crop };
    e.preventDefault();
  }

  function onMouseDown(e) {
    if (e.button !== 0) return;

    const handle = pointerInHandle(e.target);
    if (handle) {
      beginResize(e, handle);
      return;
    }

    const insideRect = hitTestRect(e.clientX, e.clientY);
    if (insideRect && crop.w > 0 && crop.h > 0) {
      beginMove(e);
      return;
    }

    beginNewSelection(e);
  }

  function onMouseMove(e) {
    if (!dragging) return;

    const imgRect = img.getBoundingClientRect();
    const cx = e.clientX - imgRect.left;
    const cy = e.clientY - imgRect.top;

    if (mode === 'new') {
      const endX = Math.max(0, Math.min(imgRect.width, cx));
      const endY = Math.max(0, Math.min(imgRect.height, cy));

      if (aspectRatio) {
        applyAspectOnNewSelection(endX, endY);
      } else {
        const x = Math.min(startX, endX);
        const y = Math.min(startY, endY);
        const w = Math.abs(endX - startX);
        const h = Math.abs(endY - startY);
        crop = { x, y, w, h };
      }
      clampCropToImage();
      renderRect();
    } else if (mode === 'move') {
      const newX = cx - moveOffsetX;
      const newY = cy - moveOffsetY;

      crop.x = newX;
      crop.y = newY;
      clampCropToImage();
      renderRect();
    } else if (mode === 'resize' && startCrop) {
      const endX = Math.max(0, Math.min(imgRect.width, cx));
      const endY = Math.max(0, Math.min(imgRect.height, cy));

      if (aspectRatio) {
        applyAspectOnResize(resizeHandle, endX, endY);
      } else {
        applyResizeWithoutAspect(resizeHandle, endX, endY);
      }
      clampCropToImage();
      renderRect();
    }
  }

  function onMouseUp() {
    if (!dragging) return;
    dragging = false;
    resizeHandle = null;
    mode = null;

    if (crop.w < 3 || crop.h < 3) {
      rect.style.display = 'none';
      if (saveBtn) saveBtn.disabled = true;
      return;
    }

    const imgRect = img.getBoundingClientRect();
    ensureNaturalSize();

    if (!naturalW || !naturalH || !imgRect.width || !imgRect.height) {
      console.warn('[cmnsd:cropper] cannot compute scaling (missing sizes)');
      return;
    }

    const scaleX = naturalW / imgRect.width;
    const scaleY = naturalH / imgRect.height;

    const payload = {
      [fieldMap.x]: Math.round(crop.x * scaleX),
      [fieldMap.y]: Math.round(crop.y * scaleY),
      [fieldMap.w]: Math.round(crop.w * scaleX),
      [fieldMap.h]: Math.round(crop.h * scaleY)
    };

    console.debug('[cmnsd:cropper] crop → natural pixels', payload);

    if (saveBtn) {
      saveBtn.dataset.body = JSON.stringify(payload);
      saveBtn.disabled = false;
    }

    wrapper.dispatchEvent(
      new CustomEvent('cmnsd:cropper:changed', {
        bubbles: true,
        detail: { crop: payload, wrapper, img }
      })
    );
  }

  // Mouse handlers
  wrapper.addEventListener('mousedown', onMouseDown);
  document.addEventListener('mousemove', onMouseMove);
  document.addEventListener('mouseup', onMouseUp);

  // Ensure natural size if image already loaded
  if (img.complete) {
    ensureNaturalSize();
  } else {
    img.addEventListener('load', ensureNaturalSize, { once: true });
  }

  console.debug('[cmnsd:cropper] bound to', wrapper);
}

export function initCropper(root = document) {
  const hosts = root.querySelectorAll('[data-cropper]');
  hosts.forEach(setupCropper);
}

// Auto-bind on DOM ready and cmnsd content
document.addEventListener('DOMContentLoaded', () => {
  initCropper(document);
});

document.addEventListener('cmnsd:content:applied', (e) => {
  const root = e.detail?.container || document;
  initCropper(root);
});