# Changelog

This file documents the history of changes and improvements made to the **cmnsd** framework, as developed iteratively with ChatGPT.

---

## [Unreleased]

### Added
- Introduced **changelog.md** to track history of changes.

---

## [0.5.0] – 2025-09-27
### Added
- Added `loadContent` as a top-level export in `core.js`, so it can be called directly via `cmnsd.loadContent(...)`.
- Added `messages.css` with styling for floating, translucent, blurred Bootstrap alerts (80% width, centered, stacked).
- Added support in `autosuggest.js` for:
  - `data-container` (to drill into nested JSON payload keys).
  - `data-extra-params` (attach extra query params).
  - Dual hidden fields (`data-field-input` and `data-field-hidden`) to allow fallback between free text and slug/id.
  - Automatic rebind on `cmnsd:content:applied` so dynamically injected inputs work.
- Added debug logs (`console.debug`) for autosuggest and actions to trace behavior.

### Changed
- Normalized all files with **2-space indentation** and English docs.
- `http.js`: `request()` no longer throws on non-200 responses; instead always returns `{ status, ok, ... }`.
- `actions.js` and `loader.js`:  
  - Always render backend messages (`response.messages`) even if status != 200.  
  - Add generic fallback `"Action failed."` or `"Load failed."` message if `ok === false`.  
  - Payload distribution/refresh only runs if `ok === true`.

### Fixed
- Fixed `getConfig is not a function` in `loader.js` by passing `getConfig` from `core.js`.
- Fixed `createActionBinder` not being exported in `actions.js` (now explicitly `export function createActionBinder`).
- Fixed `cmnsd.init is not a function` by ensuring `index.js` default export is `core`.
- Fixed `cmnsd.loadContent is not a function` by re-exporting `loadContent` in `core.js`.

---

## [0.4.0] – 2025-09-20
### Added
- Added message stacking: multiple messages can be shown below each other instead of replacing each other.
- Configurable maximum message stack (`messages.max`, default 5).
- Auto-dismiss of messages after configurable timeouts (per message level, e.g. debug after 10s, warnings after 30s).

### Changed
- Improved message box readability with translucent backgrounds and better contrast.
- Message box floats fixed at top of viewport, 80% screen width.

---

## [0.3.0] – 2025-09-15
### Added
- Introduced `autosuggest.js`:
  - Triggers after 2+ characters.
  - Renders suggestions in a dropdown list.
  - Suggestion click inserts display into input and slug/hidden field into form.
  - Works for multiple inputs automatically via `[data-autosuggest]`.
- Added delegation so autosuggest works for AJAX-inserted fields.

---

## [0.2.0] – 2025-09-10
### Added
- Introduced `actions.js` with support for delegated `[data-action]` attributes on links/buttons/forms.
- Attributes supported:
  - `data-url`, `data-method`, `data-params`, `data-body`, `data-confirm`, `data-disable`, `data-map`, `data-mode`, `data-refresh-*`.
- Safe JSON parsing and querystring fallbacks for `data-params`.

### Changed
- Loader now logs warnings instead of throwing errors when containers are missing.

---

## [0.1.0] – 2025-09-05
### Added
- Initial modularization:
  - `core.js` for central config and API.
  - `http.js` for AJAX requests with CSRF support.
  - `dom.js` for inject/update/insert utilities.
  - `messages.js` for Bootstrap message rendering.
  - `loader.js` for fetching/distributing payloads.
  - `index.js` entrypoint.
- Basic message rendering from JSON responses.
- Insert/update behavior: replace element with same `id` instead of appending duplicates.

---

