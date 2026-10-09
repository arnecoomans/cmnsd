// Small DOM helpers for cmnsd.js.
// Indentation: 2 spaces. Docs in English.

const bound = new WeakMap();

// once(el, 'filter') - true the first time for this element and key, false
// after: a per-element binder can run again on HTML it has already set up
// (enhance.js) without binding twice.
export function once(el, key) {
  let keys = bound.get(el);
  if (!keys) bound.set(el, (keys = new Set()));
  if (keys.has(key)) return false;
  keys.add(key);
  return true;
}

// closest(event, selector) - the event target's nearest match, or null;
// safe when the target is the document itself (no .closest()).
export function closest(event, selector) {
  const target = event.target;
  return target && target.closest ? target.closest(selector) : null;
}

// confirmed(el) - asks el's data-cmnsd-confirm question, if it has one;
// true when there's none or it was answered yes.
export function confirmed(el) {
  const question = el?.dataset?.cmnsdConfirm;
  return !question || window.confirm(question);
}

// asked(el) - asks el's data-cmnsd-prompt question, if it has one, for an
// answer that goes along as the field data-cmnsd-prompt-name (e.g. why
// something is revoked). null: no question; false: cancelled or left
// empty - the action doesn't go ahead; else {name, value}.
export function asked(el) {
  const question = el?.dataset?.cmnsdPrompt;
  if (!question) return null;
  const answer = window.prompt(question);
  if (answer === null || !answer.trim()) return false;
  return { name: el.dataset.cmnsdPromptName || 'answer', value: answer.trim() };
}

// busy(elements, fn) - disables the elements while fn's promise runs, and
// enables them again after (those still on the page).
export async function busy(elements, fn) {
  const list = [...elements];
  list.forEach((el) => { el.disabled = true; });
  try {
    return await fn();
  } finally {
    list.forEach((el) => { if (el.isConnected) el.disabled = false; });
  }
}
