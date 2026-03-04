# Changelog — cmnsd JavaScript Framework

## v2.1.0 — Lightbox & Modal Overlays (2026-03)

### ✨ Added
- **Lightbox** (`lightbox.js`)
  - `data-action="lightbox"` on any element opens a full-screen image overlay
  - `data-gallery` groups images for left/right arrow navigation with `n / total` counter
  - `data-caption` (fallback: img alt) renders a caption below the image
  - Keyboard: Escape=close, ArrowLeft/ArrowRight=navigate
  - Gallery items collected dynamically at click time — works correctly after AJAX updates
- **Modal** (`modal.js`)
  - `data-action="modal"` opens a centered overlay dialog
  - `data-url` fetches body HTML from server; `data-content` uses inline HTML
  - `data-content-key` selects which `response.payload` key to render (default: `content`)
  - `data-close-modal` on any element inside the modal closes it when clicked
  - Fires `cmnsd:content:applied` after rendering so autosuggest and other features reinitialize
  - Loading state shown while fetching; error state on failure
  - Keyboard: Escape closes the modal

### 🔧 Compatibility
- Both modules are standalone — zero changes to existing files
- Both auto-initialize on `DOMContentLoaded` and `cmnsd:content:applied`

---

## v2.0.0 — Clipboard Integration & Stability Fixes (2025-10)

### ✨ Added
- **Copy-to-Clipboard Action**
  - Added support for `data-action="copy"`
  - Supports both `data-text` and `data-clipboard-target`
  - Displays Bootstrap message feedback without interfering with other modules

### 🧠 Improved
- **Autosuggest stability**
  - Prevented accidental AJAX submissions when clicking in autosuggest fields
  - Improved reinitialization after AJAX updates
- **Action delegation**
  - Cleaner form vs. click differentiation to avoid duplicate requests
- **Documentation**
  - Added full data-attribute reference table
  - Expanded examples for local and remote autosuggest, multi-field display, and clipboard

### 🐛 Fixed
- Fixed `cmnsd:content:applied` event dispatch missing in certain dynamic updates
- Fixed message overlap timing in message stack logic
- Fixed tooltip persistence after AJAX-inserted elements

### 🔧 Compatibility
- Fully compatible with Django 5.x
- Works in modern browsers supporting ES6 modules and Clipboard API

---
