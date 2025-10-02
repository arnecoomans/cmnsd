# Changelog

## v0.7.1 (2025-10-02)
- **Autosuggest**: Added safe HTML rendering in suggestions.
  - Allowed tags: `<b>`, `<strong>`, `<i>`, `<em>`.
  - All other tags are stripped or flattened to plain text.
- **Autosuggest**: Ensures input box itself always shows plain text (tags removed).
- **Autosuggest**: Fixed button enabling/disabling logic:
  - If `data-allow-create="0"` → must select a valid suggestion, cannot be empty.
  - If `data-allow-create!="0"` → free text allowed, but cannot be empty.

## v0.7.0
- **Autosuggest**: Added `data-allow-create="0"` to restrict inputs to valid suggestions only.
- **Autosuggest**: Added `data-min="0"` to fetch suggestions immediately (show all options).
- **Autosuggest**: Submit button disabling logic:
  - If `data-allow-create="0"` → button only enabled when a valid suggestion is chosen.
  - If `data-allow-create!="0"` → free text allowed but empty values disabled.
- **Actions**: Improved error handling and debugging:
  - Detailed logs in `applyFromExistingPayload`.
  - More informative error messages showing which action failed.
- **DOM**: Dual dispatch of `cmnsd:content:applied` (on container and on document).
- **Framework**: General stability improvements with consistent debug logs.

## v0.6.x
- Added autosuggest hidden field creation (`data-field-input` / `data-field-hidden`).
- Added event rebinding on `cmnsd:content:applied`.
- Added CSRF handling for write requests.

## v0.5.x
- Added message stacking with max configurable in init.
- Added smoother transitions and rgba background styling for messages.

## v0.4.x
- Split framework into modular files (`core.js`, `http.js`, `dom.js`, `actions.js`, `loader.js`, `messages.js`, `autosuggest.js`).
- Introduced JSON content mapping (`map`) for loader and actions.

## v0.3.x
- Introduced bootstrap-styled message rendering with automatic dismiss.

## v0.2.x
- Initial delegated action binder (`actions.js`).
- Added DOM update/insert helpers.

## v0.1.x
- First working prototype of cmnsd: JSON loader + content injection.
