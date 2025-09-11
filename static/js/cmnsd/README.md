# cmnsd — tiny DOM + HTTP helper for Django-backed apps

A minimal, framework-agnostic ES module that centralizes:

- Fetching JSON/HTML from your Django endpoints (CSRF-aware)
- Distributing multi-key `payload` objects into containers
- Rendering Bootstrap alerts from server `messages`
- **Generic actions** via `data-*` attributes (`data-action`): click/submit handlers that fire requests without extra JS
- Helpful `console.debug` traces

**Indentation:** 2 spaces. **Docs:** English. **No bundler required** (native ES modules).

## Files

```
cmnsd/
  index.js       # public entry (default export, also sets window.cmnsd)
  core.js        # central config, composition, public API
  http.js        # fetch wrapper + CSRF + toQuery
  dom.js         # inject / insert / update / on + tiny DOM utils
  messages.js    # normalize & render Bootstrap alerts
  loader.js      # loadContent({ url, map, ... })
  actions.js     # generic data-action delegation (click/submit)
  README.md
```

## Install (Django)

```
yourapp/static/cmnsd/*  (copy files here)
```

In your template:

```html
{% load static %}
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5/dist/css/bootstrap.min.css" rel="stylesheet">

<div id="alerts"></div>
<div id="tasks"></div>
<div id="news"></div>

<script type="module">
  import cmnsd from "{% static 'cmnsd/index.js' %}";

  cmnsd.init({
    baseURL: '/api/',
    debug: true, // enable console.debug tracing
    messages: { container: '#alerts', dismissible: true, clearBefore: true },
    actions: { autoBind: true } // bind delegated [data-action] on document
  });

  // Load some sections on page-load
  cmnsd.loadContent({
    url: '/api/dashboard/summary/',
    map: { tasks_html: '#tasks', news_html: '#news' }
  });
</script>
```

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
    clearBefore?: boolean
  },
  actions?: {
    autoBind?: boolean, // default true — binds generic [data-action]
    root?: Element | Document // default document
  }
}
```

### HTTP

```js
await cmnsd.get(url, { params, headers, signal });
await cmnsd.post(url, { data, params, headers, signal });
await cmnsd.put(url, { data });
await cmnsd.patch(url, { data });
await cmnsd.delete(url, { params });
```

- Objects passed as `params` become query strings.
- `data` may be a `FormData`, `string`, `Blob`, or plain object (JSON).

### DOM helpers

```js
cmnsd.update('#container', '<div>html</div>');
cmnsd.insert('#container', '<div>append</div>'); // alias of inject
cmnsd.inject('#container', NodeOrHTML);
cmnsd.on(document, 'click', '.btn', (e, btn) => { ... });
```

### Messages

```js
cmnsd.messages.render(response); // reads response.messages/message and shows Bootstrap alerts
```

Accepted shapes:

```json
{ "message": "Saved" }
{ "messages": ["Saved", "All good"] }
{ "messages": [{ "level": "success", "text": "Saved" }] }
```

Levels map to Bootstrap: `debug→secondary`, `info→info`, `success→success`, `warning→warning`, `error→danger`.

### `cmnsd.loadContent({ url, params, map, mode, onDone })`

Fetches `url` and distributes `response.payload` into containers defined by `map`:

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
    { "level": "success", "text": "Dashboard up-to-date." }
  ]
}
```

### Generic actions via `data-action`

Add `data-action` to any **button/link/form** to make it “live” without extra JS. Everything is driven by `data-*` attributes:

Attribute | Type | Meaning
---|---|---
`data-url` | string | Endpoint. Falls back to `href` (links) or `action` (forms).
`data-method` | string | `GET`, `POST`, `PUT`, `PATCH`, `DELETE`. Defaults: link→`GET`, button/form→`POST`.
`data-params` | string | JSON object or querystring (`"a=1&b=2"`).
`data-body` | string | `"form"` (submits nearest form) or JSON string.
`data-confirm` | string | Show a confirm dialog before proceeding.
`data-disable` | present | If present, the element is disabled during the request.
`data-map` | JSON | Distribute **this response's** `payload` into containers. Example: `{"tasks_html":"#tasks"}`.
`data-mode` | string | `update` (default) or `insert` when using `data-map`.
`data-refresh-url` | string | Follow-up GET to refresh content after action succeeds.
`data-refresh-params` | string | JSON or querystring for the refresh request.
`data-refresh-map` | JSON | Map for distributing the refresh payload.
`data-refresh-mode` | string | `update` or `insert` for the refresh distribution.

Examples:

```html
<!-- Approve (POST), then refresh the dashboard sections -->
<button
  type="button"
  class="btn btn-sm btn-primary"
  data-action
  data-url="/api/tasks/123/approve/"
  data-method="POST"
  data-confirm="Approve this task?"
  data-disable
  data-refresh-url="/api/dashboard/summary/"
  data-refresh-map='{"tasks_html":"#tasks","news_html":"#news"}'
  data-refresh-mode="update"
>Approve</button>

<!-- Delete (DELETE) and use the SAME response payload to update #tasks -->
<a
  href="/api/tasks/123/"
  class="link-danger"
  data-action
  data-method="DELETE"
  data-confirm="Delete this task?"
  data-map='{"tasks_html":"#tasks"}'
  data-mode="update"
>Delete</a>

<!-- Inline create: submit the form (body=form) and update #tasks from response -->
<form data-action data-url="/api/tasks/create/" data-body="form" data-map='{"tasks_html":"#tasks"}'>
  <input name="title" required>
  <button class="btn btn-success" data-disable>Create</button>
</form>
```

## Debugging

Set `debug: true` in `init()` to see `console.debug` logs for requests, content loads, and actions.

## Notes

- CSRF token is read from cookie `csrftoken` by default; override via `csrftoken` in `init()` if needed.
- This library is framework-agnostic; Bootstrap is **only** used for alert styling.
- Works with server responses that return HTML snippets or plain strings for each payload key.

## License

MIT (add your preferred license if different).
