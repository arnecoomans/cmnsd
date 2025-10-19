
# cmnsd Framework Changelog

## Version 1.6 — Autosuggest Enhancements
**Date:** 2025-10-04

### ✨ New Features
- **Keyboard navigation:** Navigate suggestions with ↑ ↓, confirm with Enter, close with Esc.
- **Multi-field suggestions:** Show multiple fields using `data-display-fields="name,url"`.
- **Custom secondary line scaling:** `data-display-secondary-size` (default 0.8).
- **URL follow mode:** Click suggestions to open their URL via `data-onclick-follow="url"`.
- **Field prefix support:** Added `data-field-prefix` to prefix related field names (e.g. `link__id`).
- **Smart field submission:** Only submits one field — hidden (selected) or visible (typed).
- **Search mode:** New `data-search-mode="true"` keeps `q` parameter for search forms.
- **Cleaner logging:** Simplified debug messages and error handling.
- **Automatic reinit:** Rebinds autosuggest after `cmnsd:content:applied` events.

### 🐞 Fixes
- Fixed bug where both visible and hidden fields submitted simultaneously.
- Fixed potential double-binding issue when reloading dynamic content.
- Fixed empty payload overwriting values (`None` problem).
- Improved list cleanup and visual transitions.

### 🧩 Notes
- Backwards compatible with previous cmnsd autosuggest versions.
- CSS styling improved for readability and keyboard navigation.
- Recommended Bootstrap integration: `.list-group-item.active`.
