// Dropdown menus for cmnsd.js.
// Indentation: 2 spaces. Docs in English.
//
// A native <details data-cmnsd-menu> (a <summary> plus a panel) opens and
// closes without JS. This adds what a menu is expected to do: close on a
// click outside it, on Escape (focus back on its summary), and when
// another menu opens - so two menus never overlap.

import { dbg } from './context.js';

const SELECTOR = 'details[data-cmnsd-menu]';

export function bindMenus(root) {
  const menus = [...root.querySelectorAll(SELECTOR)];
  if (!menus.length) return;
  menus.forEach((menu) => menu.addEventListener('toggle', () => {
    if (!menu.open) return;
    menus.forEach((other) => { if (other !== menu) other.open = false; });
  }));
  document.addEventListener('click', (event) => {
    menus.forEach((menu) => { if (menu.open && !menu.contains(event.target)) menu.open = false; });
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    menus.forEach((menu) => {
      if (!menu.open) return;
      menu.open = false;
      menu.querySelector('summary')?.focus();
    });
  });
  dbg('menus', menus.length);
}
