// cmnsd/cropper.js
// Simple drag-to-crop helper for cmnsd.js
// - Auto-binds on [data-cropper]
// - Converts displayed selection to natural pixel coords
// - Writes JSON payload to save button's data-body
// - Supports field mapping via data-cropper-fields="x=portrait_x,y=...,w=...,h=..."
// - Shows green overlay over the selected area for debugging/preview

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

  // Find / create selection rect
  let rect = wrapper.querySelector('.cmnsd-crop-rect');
  if (!rect) {
    rect = document.createElement('div');
    rect.className = 'cmnsd-crop-rect';
    wrapper.appendChild(rect);
  }
  // Base rect styling (debug overlay: green)
  rect.style.position = 'absolute';
  rect.style.display = 'none';
  rect.style.border = '2px solid rgba(0, 255, 0, 0.9)';
  rect.style.background = 'rgba(0, 255, 0, 0.25)';
  rect.style.pointerEvents = 'none';
  rect.style.boxSizing = 'border-box';

  // Resolve save button
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

  // Field mapping
  const fieldMap = parseFieldMap(wrapper.dataset.cropperFields);

  let naturalW = 0;
  let naturalH = 0;

  function ensureNaturalSize() {
    if (naturalW && naturalH) return;
    if (img.naturalWidth && img.naturalHeight) {
      naturalW = img.naturalWidth;
      naturalH = img.naturalHeight;
    }
  }

  // Track drag
  let dragging = false;
  let startX = 0;
  let startY = 0;
  let cropDisplay = { x: 0, y: 0, w: 0, h: 0 }; // in displayed-image coords

  function beginDrag(e) {
    ensureNaturalSize();
    if (!naturalW || !naturalH) {
      console.warn('[cmnsd:cropper] natural size unknown for image', img);
      return;
    }

    const imgRect = img.getBoundingClientRect();
    const wrapperRect = wrapper.getBoundingClientRect();

    const cx = e.clientX;
    const cy = e.clientY;

    // Only start if inside image
    if (
      cx < imgRect.left ||
      cx > imgRect.right ||
      cy < imgRect.top ||
      cy > imgRect.bottom
    ) {
      return;
    }

    dragging = true;

    startX = cx - imgRect.left;
    startY = cy - imgRect.top;

    cropDisplay = { x: startX, y: startY, w: 0, h: 0 };

    // Position rect inside wrapper: image offset + local start
    const offsetLeft = imgRect.left - wrapperRect.left;
    const offsetTop = imgRect.top - wrapperRect.top;

    rect.style.left = `${offsetLeft + startX}px`;
    rect.style.top = `${offsetTop + startY}px`;
    rect.style.width = '0px';
    rect.style.height = '0px';
    rect.style.display = 'block';

    // Prevent image drag ghost
    e.preventDefault();
  }

  function updateDrag(e) {
    if (!dragging) return;

    const imgRect = img.getBoundingClientRect();
    const wrapperRect = wrapper.getBoundingClientRect();

    // Coordinates relative to image
    let currentX = e.clientX - imgRect.left;
    let currentY = e.clientY - imgRect.top;

    // Clamp inside image
    currentX = Math.max(0, Math.min(imgRect.width, currentX));
    currentY = Math.max(0, Math.min(imgRect.height, currentY));

    const x = Math.min(startX, currentX);
    const y = Math.min(startY, currentY);
    const w = Math.abs(currentX - startX);
    const h = Math.abs(currentY - startY);

    cropDisplay = { x, y, w, h };

    const offsetLeft = imgRect.left - wrapperRect.left;
    const offsetTop = imgRect.top - wrapperRect.top;

    rect.style.left = `${offsetLeft + x}px`;
    rect.style.top = `${offsetTop + y}px`;
    rect.style.width = `${w}px`;
    rect.style.height = `${h}px`;
  }

  function endDrag() {
    if (!dragging) return;
    dragging = false;

    const { x, y, w, h } = cropDisplay;
    if (w < 3 || h < 3) {
      // Too small – reset
      rect.style.display = 'none';
      if (saveBtn) saveBtn.disabled = true;
      return;
    }

    const imgRect = img.getBoundingClientRect();
    ensureNaturalSize();

    const scaleX = naturalW / imgRect.width;
    const scaleY = naturalH / imgRect.height;

    const crop = {
      [fieldMap.x]: Math.round(x * scaleX),
      [fieldMap.y]: Math.round(y * scaleY),
      [fieldMap.w]: Math.round(w * scaleX),
      [fieldMap.h]: Math.round(h * scaleY)
    };

    console.debug('[cmnsd:cropper] crop → natural pixels', crop);

    if (saveBtn) {
      saveBtn.dataset.body = JSON.stringify(crop);
      saveBtn.disabled = false;
    }

    // Fire a custom event so backend logic can hook in if desired
    wrapper.dispatchEvent(
      new CustomEvent('cmnsd:cropper:changed', {
        bubbles: true,
        detail: { crop, wrapper, img }
      })
    );
  }

  // Mouse handlers
  wrapper.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;
    beginDrag(e);
  });

  document.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    updateDrag(e);
  });

  document.addEventListener('mouseup', () => {
    if (!dragging) return;
    endDrag();
  });

  // Ensure natural size if image already loaded
  if (img.complete) {
    ensureNaturalSize();
  } else {
    img.addEventListener('load', ensureNaturalSize, { once: true });
  }

  console.debug('[cmnsd:cropper] bound cropper to', wrapper);
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