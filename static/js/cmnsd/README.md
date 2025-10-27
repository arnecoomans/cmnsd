# cmnsd JavaScript Framework
![cmnsd.js](https://raw.githubusercontent.com/arnecoomans/cmnsd/refs/heads/main/static/img/cmnsd/cmnsd_js.png "cmnsd.js logo")

## Overview
**cmnsd** is a lightweight modular JavaScript framework for Django-based projects.  
It provides AJAX-driven interactions, autosuggest inputs, and declarative HTML actions using data attributes.

---

## Core Features
1. **Action Triggers** – Perform AJAX calls or client-side actions via `data-action`.
2. **Autosuggest Inputs** – Fetch dynamic suggestions from a remote or local source.
3. **Utility Extensions** – Clipboard copy, message rendering, and content updates.

---

## 1️⃣ Action Triggers

Use `data-action` attributes to define interactive buttons, links, or forms that trigger AJAX actions or other client-side behaviors.

### Example: AJAX Call
```html
<button
  class="btn btn-danger"
  data-action
  data-method="DELETE"
  data-url="/json/location/123-camping-les-cols/"
  data-confirm="Are you sure?"
  data-refresh-url="/json/location/list/"
  data-refresh-map='{"list":"#location-list"}'
  data-refresh-mode="update"
>
  Delete Location
</button>
```

### Example: Copy to Clipboard
```html
<button
  class="btn btn-outline-primary"
  data-action="copy"
  data-text="https://example.com/invite"
  data-message="Link copied to clipboard!"
>
  Copy link
</button>

<!-- Or copy from another element -->
<pre id="invite-code">ABC-123</pre>
<button
  class="btn btn-outline-secondary"
  data-action="copy"
  data-clipboard-target="#invite-code"
  data-message="Copied code!"
>
  Copy Code
</button>
```

---

## 2️⃣ Autosuggest Inputs

Autosuggest allows smart text fields that fetch or filter data dynamically.

### Remote Example
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
  data-display-fields="name,description"
/>
```

### Local Example
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
  data-allow-create="0"
/>
```

### Search Mode Example
```html
<input
  type="text"
  class="form-control"
  placeholder="Search locations..."
  data-autosuggest
  data-url="/json/locations/"
  data-param="q"
  data-search-mode="true"
  data-min="1"
/>
```

---

## 3️⃣ Message Handling

Messages from server or client-side events are shown using Bootstrap-style alerts.

### Example Backend Response
```json
{
  "messages": [
    {"level": "success", "message": "Tag added successfully!"}
  ]
}
```

### Example Display
```
✅ Tag added successfully!
```

---

## Supported Attributes

| Attribute | Module | Description |
|------------|----------|-------------|
| `data-action` | actions.js | Declares element as actionable trigger |
| `data-method` | actions.js | HTTP method (GET, POST, PATCH, DELETE) |
| `data-url` | actions.js | AJAX endpoint URL |
| `data-confirm` | actions.js | Confirmation prompt before request |
| `data-map` | actions.js | Maps payload keys to DOM targets |
| `data-refresh-url` | actions.js | Follow-up fetch after success |
| `data-action="copy"` | actions.js | Copies text or target content to clipboard |
| `data-autosuggest` | autosuggest.js | Enables autosuggest behavior |
| `data-local-source` | autosuggest.js | Inline JSON for local suggestions |
| `data-display-fields` | autosuggest.js | Fields to display in dropdown |
| `data-onclick-follow="url"` | autosuggest.js | Follows suggestion URL when clicked |

---

## Example Combined Form

```html
<form
  action="/json/location/1-camping-les-cols/tags/"
  data-action
  data-method="POST"
  data-body="form"
  data-map='{"tags":"#tags"}'
>
  <input
    type="text"
    class="form-control"
    placeholder="Add tag..."
    data-autosuggest
    data-url="/json/tags/"
    data-param="q"
    data-container="tags"
    data-field-input="name"
    data-field-hidden="slug"
  >
  <button type="submit" class="btn btn-primary mt-2">Add</button>
</form>
```

This form:
- Provides autosuggest for tags.  
- Submits via AJAX.  
- Updates `#tags` on success.  
- Shows messages.

---

## File Overview
```
cmnsd/
├── actions.js        # Handles data-action logic and AJAX
├── autosuggest.js    # Local + remote autosuggest overlay
├── core.js           # Main initializer
├── dom.js            # DOM update utilities
├── http.js           # AJAX with CSRF support
├── loader.js         # Maps payloads to DOM
├── messages.js       # Bootstrap message rendering
├── index.js          # Entry point
```

---

## Events

| Event | Description |
|--------|-------------|
| `cmnsd:autosuggest:shown` | Autosuggest dropdown shown |
| `cmnsd:autosuggest:hidden` | Autosuggest dropdown hidden |
| `cmnsd:autosuggest:selected` | Suggestion clicked |
| `cmnsd:autosuggest:positioned` | Dropdown positioned |

---

## License
MIT License — © 2025 Arne Coomans
