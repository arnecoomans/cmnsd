// Regions on an image, linked to what they're about, for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// The project renders the regions itself (a box per region, placed in
// percent over the image - cmnsd RegionMixin's fractions), marked
//   data-cmnsd-region="<key>"        e.g. a person's token
// and elsewhere on the page what each is about:
//   data-cmnsd-region-for="<key>"    e.g. that person's card
// Hovering or focusing either side gives every element with that key the
// class `is-linked` - the frame lights up with its card, and the card with
// its frame. Delegated on the document: elements added later work too.
// Without JS: the regions are there, unlinked.
//
// The element the regions are drawn on, marked data-cmnsd-regions-area: while
// any of its regions shows, a click or tap on it is about the regions, never
// its link (a lightbox, full screen) - on a phone there's no hovering, so a
// tap on a region shows it: the class `is-tapped` on it and what it's for,
// until it's tapped again (a separate class: a phone's simulated mouse-out
// after a tap clears is-linked). A tap elsewhere on the image clears it. With
// no region showing (switched off, or another image in a browser), clicks go
// through as ever.
//
// Marking one: a button marked
//   data-cmnsd-mark="<selector>"      the element over the image (its box)
//   data-cmnsd-mark-hint="<text>"     optional, shown while marking
// inside a form with inputs region_x, region_y, region_w, region_h starts
// marking on that element: drag a box, or click for a point (w = h = 0) -
// fractions of the element, as RegionMixin stores them - and the form is
// sent (actions.js: data-cmnsd-action). Escape cancels. While marking, a
// click on the image doesn't follow its link (a lightbox). Not while an
// image browser around it shows another item (gallery.js
// data-gallery-showing="other"): the regions are the page's own image's.

const ANY = '[data-cmnsd-region], [data-cmnsd-region-for]';

function keyOf(el) {
  return el.dataset.cmnsdRegion || el.dataset.cmnsdRegionFor || '';
}

let tapped = '';   // the region shown by a tap (a phone: no hovering)

function showing(area) {
  return [...area.querySelectorAll('[data-cmnsd-region]')].some((region) => region.getClientRects().length > 0);
}

function onAreaClick(event) {
  if (marking || swallow) return;   // marking handles its own clicks
  const area = event.target.closest?.('[data-cmnsd-regions-area]');
  if (!area || !showing(area)) return;
  event.preventDefault();
  event.stopPropagation();
  const region = event.target.closest('[data-cmnsd-region]');
  const key = region ? keyOf(region) : '';
  if (tapped) mark(tapped, false, 'is-tapped');
  tapped = key && key !== tapped ? key : '';
  if (tapped) mark(tapped, true, 'is-tapped');
}

function mark(key, on, className = 'is-linked') {
  if (!key) return;
  const selector = `[data-cmnsd-region="${CSS.escape(key)}"], [data-cmnsd-region-for="${CSS.escape(key)}"]`;
  document.querySelectorAll(selector).forEach((el) => el.classList.toggle(className, on));
}

export function bindRegions(root) {
  root.addEventListener('click', onAreaClick, true);   // capture: before the image's link
  ['mouseover', 'focusin'].forEach((type) => root.addEventListener(type, (event) => {
    const el = event.target.closest?.(ANY);
    if (el) mark(keyOf(el), true);
  }));
  ['mouseout', 'focusout'].forEach((type) => root.addEventListener(type, (event) => {
    const el = event.target.closest?.(ANY);
    if (!el) return;
    const into = event.relatedTarget?.closest?.(ANY);
    if (into && keyOf(into) === keyOf(el)) return;   // still within the same one
    mark(keyOf(el), false);
  }));
}

// --- Marking -----------------------------------------------------------------

const POINT = 0.01;   // smaller than this, both ways: a click - a point
let marking = null;   // {form, target, hint, start, box}
// The click a browser fires right after the pointerup that finished marking:
// it would reach the image's link (a lightbox) - swallowed, once.
let swallow = null;   // the element it would land in

function fraction(value) {
  return Math.min(Math.max(value, 0), 1);
}

function at(event, target) {
  const rect = target.getBoundingClientRect();
  return { x: fraction((event.clientX - rect.left) / rect.width), y: fraction((event.clientY - rect.top) / rect.height) };
}

function stop() {
  if (!marking) return;
  marking.target.classList.remove('is-marking');
  marking.box?.remove();
  marking.hint?.remove();
  marking = null;
}

function draw(from, to) {
  const left = Math.min(from.x, to.x);
  const top = Math.min(from.y, to.y);
  Object.assign(marking.box.style, {
    left: `${left * 100}%`, top: `${top * 100}%`,
    width: `${Math.abs(to.x - from.x) * 100}%`, height: `${Math.abs(to.y - from.y) * 100}%`,
  });
}

function finish(from, to) {
  const { form } = marking;
  let box;
  if (Math.abs(to.x - from.x) < POINT && Math.abs(to.y - from.y) < POINT) {
    box = [from.x, from.y, 0, 0];   // a point
  } else {
    box = [Math.min(from.x, to.x), Math.min(from.y, to.y), Math.abs(to.x - from.x), Math.abs(to.y - from.y)];
  }
  ['region_x', 'region_y', 'region_w', 'region_h'].forEach((name, index) => {
    const input = form.querySelector(`[name="${name}"]`);
    if (input) input.value = box[index].toFixed(4);
  });
  swallow = marking.target;
  setTimeout(() => { swallow = null; }, 500);   // no click came (a touch): forget it
  stop();
  form.requestSubmit();
}

export function bindRegionMarking(root) {
  root.addEventListener('click', (event) => {
    const button = event.target.closest?.('[data-cmnsd-mark]');
    if (button) {
      event.preventDefault();
      const target = document.querySelector(button.dataset.cmnsdMark);
      const form = button.closest('form');
      if (!target || !form || target.closest('[data-gallery-showing="other"]')) return;
      stop();
      target.classList.add('is-marking');
      const box = document.createElement('span');
      box.className = 'cmnsd-region-draft';
      box.hidden = true;
      target.append(box);
      let hint = null;
      if (button.dataset.cmnsdMarkHint) {
        hint = document.createElement('p');
        hint.className = 'cmnsd-region-hint';
        hint.textContent = button.dataset.cmnsdMarkHint;
        (target.closest('a') || target).insertAdjacentElement('afterend', hint);   // below the image, not in its link
      }
      marking = { form, target, hint, box, start: null };
      target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
    // While marking - and the click right after it ends: the marking, not the image's link.
    const area = marking?.target || swallow;
    if (area && area.contains(event.target)) {
      event.preventDefault();
      event.stopPropagation();
      swallow = null;
    }
  }, true);
  root.addEventListener('pointerdown', (event) => {
    if (!marking || !marking.target.contains(event.target)) return;
    event.preventDefault();
    marking.start = at(event, marking.target);
    marking.box.hidden = false;
    draw(marking.start, marking.start);
    marking.target.setPointerCapture?.(event.pointerId);
  });
  root.addEventListener('pointermove', (event) => {
    if (!marking?.start) return;
    draw(marking.start, at(event, marking.target));
  });
  root.addEventListener('pointerup', (event) => {
    if (!marking?.start) return;
    finish(marking.start, at(event, marking.target));
  });
  root.addEventListener('keydown', (event) => {
    if (marking && event.key === 'Escape') {
      event.preventDefault();
      stop();
    }
  });
}
