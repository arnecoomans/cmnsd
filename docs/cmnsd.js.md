# cmnsd.js — Frontend Action & Content System

## Overview

`cmnsd.js` is a modular ES-module library that wires Django's cmnsd.api responses
into the DOM. It handles AJAX actions, content injection, message rendering, and
autosuggest. Loaded as `type="module"` and initialized via `cmnsd.init({...})`.

Source: `cmnsd/static/js/cmnsd/`

---

## Module map

| File | Purpose |
|---|---|
| `index.js` | Entry point — re-exports core |
| `core.js` | Initializer, wires all modules together, exposes `init()` / `loadContent` |
| `http.js` | `fetch` wrapper with CSRF, JSON, credentials (`api.get/post/patch/delete`) |
| `actions.js` | Delegated `data-action` click/submit handler |
| `loader.js` | `loadContent()` — fetches URL, distributes `payload` keys into DOM containers |
| `dom.js` | `update()` / `insert()` / `inject()` DOM helpers; Bootstrap tooltip lifecycle |
| `messages.js` | Normalize + render server messages into a configured container |
| `autosuggest.js` | `data-autosuggest` input → live search dropdown + hidden field pattern |
| `modal.js` | Bootstrap modal loader via `data-action="modal"` |
| `lightbox.js` | Image lightbox via `data-action="lightbox"` |

---

## Initialization

```html
<script type="module">
  import cmnsd from '{% static "js/cmnsd/index.js" %}';
  cmnsd.init({
    debug: false,
    messages: { container: '#messages', dismissible: true, max: 5 },
    actions: { autoBind: true }
  });
</script>
```

`autoBind: true` (default) delegates click and submit listeners to `document`.

---

## data-action pattern (actions.js)

Any element with `data-action` is intercepted. Click for links/buttons, submit for forms.

```html
<!-- GET request, update container -->
<a href="/api/locations/"
   data-action
   data-map='{"location": "#location-card"}'>
  Reload
</a>

<!-- POST with form body, then refresh another section -->
<form data-action data-body="form"
      data-refresh-url="/api/locations/"
      data-refresh-map='{"location": "#card"}'
      action="/api/locations/">
  ...
</form>
```

Key `data-*` attributes:
- `data-action` — required; value can be empty, `"info"`, `"copy"`, `"modal"`, `"lightbox"`
- `data-url` — override URL (defaults to `href`/`action`)
- `data-method` — HTTP method (defaults: `GET` for `<a>`, form method otherwise)
- `data-params` — extra query params (JSON object or querystring)
- `data-body` — `"form"` serializes nearest form; `"#id"` serializes that form; JSON literal otherwise
- `data-map` — JSON `{"payload_key": "#css-selector"}` — distributes response payload into DOM
- `data-mode` — `"insert"` (append) or `"update"` (replace, default)
- `data-refresh-url` / `data-refresh-map` / `data-refresh-mode` — secondary fetch after action
- `data-confirm` — confirmation dialog text before executing

---

## loadContent (loader.js)

```javascript
import { loadContent } from 'cmnsd/index.js';

await loadContent({
  url: '/api/locations/',
  params: { scope: 'accommodations' },
  map: { location: '#location-list' },
  mode: 'update'   // or 'insert'
});
```

Fetches `url`, reads `response.payload`, maps each key to a DOM container.

---

## dom.update vs dom.insert

- `update(container, html)` — replaces all children; disposes/re-inits Bootstrap tooltips;
  fires `cmnsd:content:applied` event.
- `insert(container, html, {position})` — appends (or prepends) nodes; deduplicates by `id`;
  fires `cmnsd:content:applied` event.
- Both accept a CSS selector string or a DOM element as `container`.

---

## autosuggest pattern

```html
<input type="text"
  data-autosuggest
  data-url="{% url 'cmnsd:dispatch' 'categories' %}"
  data-param="q"
  data-extra-params='{"format":"json"}'
  data-field-input="name"
  data-field-hidden="slug"
  data-field-prefix="categories__"
  data-container="category"
  data-allow-create="0"
  data-min="0"
>
```

Creates a hidden `<input name="categories__slug">` alongside the visible text input.
Clears the hidden value when the text field is cleared (and disables submit button
if a value was set). A paired container with `data-container="category"` shows a
confirmation badge after selection.

---

## cmnsd:content:applied event

Fired by `dom.update` and `dom.insert` after content is injected. Used internally
to re-initialize `autosuggest` and `textarea[data-autoresize]` in new content.
Listen to it when you inject content that contains cmnsd-managed widgets.
