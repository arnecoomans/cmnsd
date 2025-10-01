# cmnsd

> ⚡ This framework was created iteratively with ChatGPT.
 — tiny DOM + HTTP + UI helpers for Django-backed apps

A minimal, framework-agnostic ES module that centralizes:

- Fetching JSON/HTML from your Django endpoints (CSRF-aware)  
- Distributing multi-key `payload` objects into containers  
- Rendering Bootstrap alerts from server `messages` (even on error responses)  
- **Generic actions** via `data-*` attributes (`data-action`)  
- **Autosuggest** feature: adds autocomplete inputs driven by JSON endpoints  
- Helpful `console.debug` traces  

**Indentation:** 2 spaces. **Docs:** English. **No bundler required** (native ES modules).

---

## Files

```
cmnsd/
  index.js        # public entry (default export, also sets window.cmnsd)
  core.js         # central config, composition, public API
  http.js         # fetch wrapper + CSRF + toQuery (never throws on !ok)
  dom.js          # inject / insert / update / on + dispatches cmnsd:content:applied
  messages.js     # normalize & render Bootstrap alerts with stacking + auto-dismiss
  loader.js       # loadContent({ url, map, ... }) (renders messages even on error)
  actions.js      # generic data-action delegation (click/submit, shows messages even on error)
  autosuggest.js  # auto-initializes [data-autosuggest] inputs
  messages.css    # styling for floating alerts
  README.md
```

---

## Install (Django)

```
yourapp/static/cmnsd/*  (copy files here)
```

In your template:

```html
{% load static %}
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="{% static 'cmnsd/messages.css' %}" rel="stylesheet">

<div id="messages" class="cmnsd-messages"></div>

<script type="module">
  import cmnsd from "{% static 'cmnsd/index.js' %}";
  import { initAutosuggest } from "{% static 'cmnsd/autosuggest.js' %}";

  cmnsd.init({
    baseURL: '/api/',
    debug: true,
    messages: { container: '#messages', dismissible: true, clearBefore: false, max: 5 },
    actions: { autoBind: true }
  });

  cmnsd.loadContent({
    url: '/api/dashboard/summary/',
    map: { tasks_html: '#tasks', news_html: '#news' }
  });

  initAutosuggest(); // autosuggest also rescans automatically after content loads
</script>
```

---

## API

### `cmnsd.init(options)`

Global options (all optional):

```ts
{
  baseURL?: string,
  headers?: Record<string, string>,
  csrftoken?: string | null,
  credentials?: 'omit' | 'same-origin' | 'include',
  beforeRequest?: (ctx: { url: string, init: RequestInit }) => void | Promise<void>,
  afterResponse?: (res: Response) => void | Promise<void>,
  onError?: (error: unknown) => void,
  debug?: boolean,
  messages?: {
    container?: string | Element,
    dismissible?: boolean,
    clearBefore?: boolean, // default false
    max?: number           // max stacked messages (default 5)
  },
  actions?: {
    autoBind?: boolean, // default true
    root?: Element | Document
  }
}
```

---

### HTTP

```js
await cmnsd.get(url, { params, headers, signal });
await cmnsd.post(url, { data, params, headers, signal });
await cmnsd.put(url, { data });
await cmnsd.patch(url, { data });
await cmnsd.delete(url, { params });
```

- `params` → query string (object or querystring).  
- `data` → `FormData`, `string`, `Blob`, or plain object (JSON).  
- ✅ Returns `{ status, ok, ...json }` even on non-200.  

---

### DOM helpers

```js
cmnsd.update('#container', '<div>html</div>');
cmnsd.insert('#container', '<div>append</div>', { position: 'top' });
cmnsd.inject('#container', NodeOrHTML); // legacy
cmnsd.on(document, 'click', '.btn', (e, btn) => { ... });
```

- `insert` replaces an element with same `id` if present, otherwise adds new content.  
- `update` clears and replaces all content.  
- After `insert`/`update`, a `cmnsd:content:applied` event is dispatched, so other features (like autosuggest) can re-scan.  

---

### Messages

```js
cmnsd.messages.render(response); // reads response.messages/message and shows alerts
```

- Supports `{ message: "Saved" }`  
- Supports `{ messages: ["Saved", "All good"] }`  
- Supports `{ messages: [{ level: "success", text: "Saved" }] }`  
- Supports `{ messages: [{ level: "info", message: "Saved" }] }`  
- Also handles `{ rendered: "<div class='alert ...'>...</div>" }`  

**Features**:
- Stacks messages (default `clearBefore: false`).  
- Auto-dismiss per level (configurable durations).  
- Max stack (default 5).  
- Fixed, centered alert container (`.cmnsd-messages`), with translucent Bootstrap colors, blur, rounded corners, and shadow.  
- ✅ Messages are rendered even on error responses.  

---

### Message Styling (`messages.css`)

See included `messages.css` for styling. Alerts are translucent, blurred, and stack at the top center of the viewport.

---

### `cmnsd.loadContent({ url, params, map, mode, onDone })`

Fetches `url` and distributes `response.payload` into containers defined by `map`.

```js
await cmnsd.loadContent({
  url: '/api/dashboard/summary/',
  params: { today: 1 },
  map: {
    tasks_html: '#tasks',
    news_html: '#news'
  },
  mode: 'update' // or 'insert'
});
```

Expected server response:

```json
{
  "payload": {
    "tasks_html": "<ul>...</ul>",
    "news_html": "<article>...</article>"
  },
  "messages": [
    { "level": "success", "text": "Dashboard updated." }
  ]
}
```

**Behavior:**  
- ✅ Renders messages even when `ok === false`.  
- ✅ Adds a generic `"Load failed."` danger message on non-200.  
- ✅ Only updates containers if `ok === true`.  

---

### Generic actions via `data-action`

Attributes:

| Attribute              | Meaning                                                  |
|------------------------|----------------------------------------------------------|
| `data-action`          | Activate element as action trigger                       |
| `data-url`             | Endpoint (falls back to `href` or `action`)              |
| `data-method`          | GET/POST/PUT/PATCH/DELETE (default: link=GET, form=POST) |
| `data-params`          | JSON or querystring (`{"a":1}` or `a=1`)                 |
| `data-body`            | `"form"` (submits nearest form) or JSON string           |
| `data-confirm`         | Confirm dialog                                           |
| `data-disable`         | Disable element during request                           |
| `data-map`             | Map payload keys to selectors (update from response)     |
| `data-mode`            | `update` (default) or `insert`                           |
| `data-refresh-url`     | Follow-up GET to refresh content                         |
| `data-refresh-params`  | Params for refresh                                       |
| `data-refresh-map`     | Map for refresh payload                                  |
| `data-refresh-mode`    | Mode for refresh (`update`/`insert`)                     |

Example:

```html
<a
  href="/api/tasks/123/"
  data-action
  data-method="DELETE"
  data-confirm="Delete?"
  data-map='{"tasks_html":"#tasks"}'
>[X]</a>
```

**Behavior:**  
- ✅ Renders messages even when `ok === false`.  
- ✅ Adds a generic `"Action failed."` danger message on non-200.  
- ✅ Only updates/refreshes containers if `ok === true`.  

---

### Autosuggest (`autosuggest.js`)

Any `<input>` with `data-autosuggest` is automatically initialized. Works on page-load and for AJAX-inserted content.

```html
<input
  type="text"
  name="tag"
  class="form-control"
  data-autosuggest
  data-url="/json/locations/suggest/"
  data-param="q"
  data-container="tags"
  data-field-input="name"
  data-field-hidden="slug"
  data-extra-params='{"format":"json"}'
/>
```

**Features:**

- Shows suggestions from server after 2+ chars.  
- Supports `data-container` to drill into nested payloads (e.g. `payload.tags`).  
- Supports `data-extra-params` to add query params.  
- Creates (or reuses) hidden fields for both `data-field-hidden` and `data-field-input`.  
- If suggestion with `slug` is clicked → submits `slug=<slug>`.  
- If free text typed → submits `name=<value>`.  
- Automatically rebinds after every `cmnsd:content:applied`.  

Example server response:

```json
{
  "payload": {
    "tags": {
      "klein-zwembad": { "slug": "klein-zwembad", "name": "Klein Zwembad" },
      "opzetzwembad": { "slug": "opzetzwembad", "name": "Opzetzwembad" }
    }
  }
}
```

---

## Debugging

- Set `debug: true` in `init()` to log requests, loads, actions, and messages.  
- Autosuggest logs to `[cmnsd:autosuggest]`.  

---

## License

MIT (add your preferred license if different).
