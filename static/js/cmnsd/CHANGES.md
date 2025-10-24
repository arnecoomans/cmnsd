# Changelog

## v1.9.0 — October 2025

### Added
- Clipboard copy feature using `data-action="copy"` and `data-clipboard-target`.
- Extended documentation for all three framework pillars (Actions, Autosuggest, Utilities).

### Improved
- Local autosuggest logic now supports case-insensitive substring search.
- Overlay portal (`#cmnsd-overlays`) ensures dropdowns escape card and modal overflow.
- Bootstrap tooltip cleanup in `dom.js` before updates.

### Fixed
- Residual tooltip elements after AJAX updates.
- Synchronization of hidden/visible fields in autosuggest forms.
