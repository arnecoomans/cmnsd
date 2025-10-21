# Changelog

## v1.8.0 — October 2025
**Enhancements**
- Added support for `data-local-source` for in-memory local autosuggest lists.
- Local search uses case-insensitive substring matching (“al” → “alice”, “albert”).
- Unified fetch logic to simplify both remote and local handling.
- Overlay rendering improved (`#cmnsd-overlays` portal auto-created).
- Optimized event dispatch system for extension compatibility.
- Cleaner internal state management and keyboard navigation improvements.

**Fixed**
- Dropdown clipping inside Bootstrap cards/modals (overlay portal).
- Submissions with both hidden and visible fields could duplicate payloads — now synchronized.

---
## v1.7.1
- Added safe HTML rendering (`<b>`, `<i>`, `<strong>`, `<em>`).

## v1.7.0
- Added multi-field display (`data-display-fields`).
- Added `data-onclick-follow="url"` behavior.
- Added semantic linker extension hooks.

## v1.6.0
- Introduced overlay rendering portal system.
- Added keyboard navigation (↑ ↓ Enter Esc).
