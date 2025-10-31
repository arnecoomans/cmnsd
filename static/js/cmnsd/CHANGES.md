# Changelog — cmnsd JavaScript Framework

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
