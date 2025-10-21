# cmnsd JavaScript Framework

## Overview
`cmnsd` is a lightweight, extensible JavaScript framework for AJAX-driven Django applications.
It provides a modular system for dynamic content loading, messaging, autosuggest inputs, and action handling.

---

## Autosuggest

The `autosuggest.js` module enables smart text inputs that can fetch or filter suggestions dynamically.
It supports both **remote AJAX requests** and **local data sources**, keyboard navigation, and overlay rendering.

### Features
- Overlay-based dropdown (`#cmnsd-overlays`) — avoids clipping in modals/cards
- Remote JSON fetching via `data-url`
- Local in-memory suggestions via `data-local-source`
- Multi-field display with different font sizes
- Substring search (“al” → “Alice”, “Albert”)
- Follow URL on click (`data-onclick-follow="url"`)
- Create new entries if allowed (`data-allow-create`)
- Auto-disable submit button for invalid values
- Rebinds automatically after AJAX updates (`cmnsd:content:applied`)
- Extension hooks via custom events

---

## Data Attributes

| Attribute | Default | Description |
|------------|----------|-------------|
| `data-url` | — | Remote URL for AJAX suggestions. Ignored if `data-local-source` is defined. |
| `data-local-source` | — | JSON list or array of local items for private/local filtering. |
| `data-min` | `2` | Minimum number of characters before search starts. |
| `data-debounce` | `300` | Delay (ms) before triggering fetch after typing. |
| `data-param` | `q` | Query parameter name for remote requests. |
| `data-field-input` | `name` | Field used for display and plain text submission. |
| `data-field-hidden` | `slug` | Field name for hidden input (used for IDs or tokens). |
| `data-container` | — | Key within JSON payload to extract list of items. |
| `data-allow-create` | `1` | Allow free text entry. Set to `0` to require valid suggestions. |
| `data-onclick-follow` | — | When set to `"url"`, clicking a suggestion follows its URL. |
| `data-display-fields` | `name` | Comma-separated list of fields to display (e.g. `"name,url"`). |
| `data-display-secondary-size` | `0.8` | Font size factor for secondary fields. |
| `data-field-prefix` | — | Prefix added to hidden and visible field names. |
| `data-search-mode` | `false` | Keeps `?q=` parameter style for general search bars. |
| `data-extra-params` | — | JSON object of additional query params for remote fetches. |

---

## Example Usage

### Remote source
```html
<input
  type="text"
  class="form-control"
  placeholder="Search tags..."
  data-autosuggest
  data-url="/json/tags/"
  data-param="q"
  data-container="tags"
  data-field-input="name"
  data-field-hidden="slug"
/>
```

### Local source
```html
<input
  type="text"
  class="form-control"
  placeholder="Select user..."
  data-autosuggest
  data-local-source='[{"id":1,"name":"Alice"},{"id":2,"name":"Bob"}]'
  data-field-input="name"
  data-field-hidden="id"
  data-min="0"
/>
```

---

## Events

| Event | Detail |
|--------|---------|
| `cmnsd:autosuggest:shown` | `{ host }` — dropdown rendered |
| `cmnsd:autosuggest:hidden` | `{ host }` — dropdown hidden |
| `cmnsd:autosuggest:selected` | `{ host, item }` — item clicked or chosen |
| `cmnsd:autosuggest:positioned` | `{ host }` — dropdown repositioned |

---

## Styling

Use `autosuggest.css` to style dropdowns, shadows, and hover behavior.

```html
<link rel="stylesheet" href="{% static 'css/autosuggest.css' %}">
```

---

## License
© 2025 Arne Coomans — Released under the MIT License.
