// "Via": how you got here, for cmnsd.js - one level deep.
// Indentation: 2 spaces. Docs in English.
//
// On the page you come from, a region marked
//   data-cmnsd-via-links="<kind>:<token>"     e.g. "tag:aB3dE5fG7h"
// gets ?via_<kind>=<token> added to each link to another page inside it
// (a tag page's people and content). On the page you arrive at, an element
// marked
//   data-cmnsd-via="<kind>:<token>"            e.g. the tag chip itself
// that matches a via_<kind> in the address gets the class `is-via` and a
// title saying so - the project's CSS makes it stand out.
//
// One level deep: the parameter is added on the region's page only, never
// passed on - links on the page you arrive at stay clean. Per element
// (enhance.js), so a region's content loaded later (an opened section, a
// live list) is linked too, and an element that arrives later (deferred
// tags) is still found. Without JS: plain links, no highlight.

import { once } from './dom.js';

const VIA_LINKS = '[data-cmnsd-via-links]';
const VIA = '[data-cmnsd-via]';

// via_<kind>=<token> pairs in the address, as "kind:token" strings.
function arrivedVia() {
  const params = new URLSearchParams(window.location.search);
  return new Set([...params].filter(([key, value]) => key.startsWith('via_') && value).map(([key, value]) => `${key.slice(4)}:${value}`));
}

// A link to another page of this site - not an anchor, a file download, an
// API address or one that already says how it was reached.
function isPageLink(link) {
  const href = link.getAttribute('href') || '';
  if (!href.startsWith('/') || href.startsWith('//') || link.hasAttribute('download')) return false;
  const url = new URL(href, window.location.origin);
  return !url.pathname.startsWith('/api/') && !url.pathname.includes('/file/') && ![...url.searchParams.keys()].some((key) => key.startsWith('via_'));
}

function addVia(link, region) {
  if (!once(link, 'via')) return;
  const [kind, token] = region.dataset.cmnsdViaLinks.split(':');
  if (!kind || !token || !isPageLink(link)) return;
  const url = new URL(link.getAttribute('href'), window.location.origin);
  url.searchParams.set(`via_${kind}`, token);
  link.setAttribute('href', url.pathname + url.search + url.hash);
}

export function bindVia(root) {
  // Links inside a region - also when root is (inside) one, e.g. a section body.
  const links = root.matches?.('a[href]') ? [root] : [...root.querySelectorAll('a[href]')];
  links.forEach((link) => {
    const region = link.closest(VIA_LINKS);
    if (region) addVia(link, region);
  });
  // What you came here through.
  const arrived = arrivedVia();
  if (!arrived.size) return;
  const marked = root.matches?.(VIA) ? [root] : [...root.querySelectorAll(VIA)];
  marked.filter((el) => arrived.has(el.dataset.cmnsdVia) && once(el, 'via-mark')).forEach((el) => {
    el.classList.add('is-via');
    if (el.dataset.cmnsdViaTitle) el.title = el.title ? `${el.title} · ${el.dataset.cmnsdViaTitle}` : el.dataset.cmnsdViaTitle;
  });
}
