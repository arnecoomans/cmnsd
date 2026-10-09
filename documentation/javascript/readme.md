# cmnsd.js

The client side of cmnsd, in `static/cmnsd.js/`: plain ES modules, no build step, no jQuery. Each module enhances server-rendered markup marked with `data-cmnsd-*` attributes. Without JavaScript every page still works - forms submit, links navigate, sections are open.

## Setup

Once, in the project's `base.html` (see [Installation](../installation.md)):

```django
{% if user.is_authenticated %}<meta name="csrf-token" content="{{ csrf_token }}">{% endif %}
...
<script type="module">
  import cmnsd from "{% static 'cmnsd.js/index.js' %}";
  cmnsd.init({
    apiRoot: '/api/',
    sectionStateUrl: '{% url "cmnsd_ui:section_state" %}',
    sortStateUrl: '{% url "cmnsd_ui:sort_state" %}',
    debug: {{ debug|yesno:'true,false' }},
  });
</script>
```

| Option | Default | |
|---|---|---|
| `apiRoot` | `'/api/'` | Where `cmnsd.api_urls` is included |
| `sectionStateUrl` | none | Where collapsible sections save open/closed; without it nothing is saved |
| `sortStateUrl` | none | Where sort switches save their choice |
| `debug` | `false` | Log requests and skipped elements to the console, prefixed `[cmnsd]` |

`{{ debug }}` is only true with `DEBUG` on and the request from `INTERNAL_IPS`.

## From a project's own script

```js
import cmnsd from "/static/cmnsd.js/index.js";

container.innerHTML = html;
cmnsd.enhance(container);          // bind every module to new HTML
cmnsd.message('Saved', 'success'); // a notice in the message area
```

Every cmnsd module already enhances the HTML it puts on the page itself; `enhance()` is for HTML a project script inserts. It's safe to call twice. `load()` is its older name.

## The pages

| Page | Modules |
|---|---|
| [Loading and sections](loading.md) | `fields.js` - values filled in after the page loads; `sections.js` - collapsible sections |
| [Lists](lists.md) | `list.js` - search while typing; `filter.js` - filter pills; `sort.js` - sort switch |
| [Actions and messages](actions.md) | `actions.js` - buttons and forms that call an API action; `messages.js`; `hints.js`; `toggles.js`; `menus.js` |
| [Editing](editing.md) | `edit.js` - editable blocks; `picker.js`; `dialog.js`; `suggest.js`; `autosave.js` |
| [Images and uploads](media.md) | `gallery.js`, `viewer.js`, `lightbox.js`, `upload.js` |
| [Via](via.md) | `via.js` - how you got here: the tag, place or person you came through, highlighted |

And the shared modules every other one uses:

| Module | Role |
|---|---|
| `index.js` | `init()`, `enhance()`, `message()`; registers every module |
| `context.js` | The settings `init()` received, and the debug logger |
| `enhance.js` | Runs every per-element binder on new HTML |
| `api.js` | The one request client - see below |
| `csrf.js` | The CSRF token: the meta tag, else the `csrftoken` cookie |
| `dom.js` | Small helpers: `once`, `closest`, `confirmed`, `busy` |

## Requests

Every module talks to the server through `request(url, options)` in `api.js`: JSON and CSRF headers, the [API response shape](../api.md) - also when the answer isn't JSON - and the response's `messages` shown. Options: `method`, `json` or `form` (the body), `signal` (abort), `messages` (`'show'`, `'keep'` for after a reload, `'none'`). It returns `{ok, status, data}`; on an error `data.error` is always a readable sentence.

`latest(fn, delay)` is "search while typing": wait for a pause, run, and abort the request before - used by lists, pickers, suggestions and hints.

## How modules bind

- **Once, on the document** - actions, edit blocks, dialogs' create buttons, lightboxes, suggestions, toggles, messages, menus: one listener, so HTML added later works by itself (menus excepted: only those on the page at start).
- **Per element** - lists, filters, sorts, sections, galleries, pickers, viewers, autosave, uploads, hints, deferred fields: registered with `enhance.js`, run on the document at start and on every piece of HTML a module inserts. Each binder marks what it bound (`dom.js once()`), so running twice binds once.

A new module picks one of the two, and adds itself in `index.js`.

## Writing a module

Plain ES module, 2-space indentation, a header comment that says what markup it enhances and with which attributes. Settings come from `context.js`, requests go through `api.js`, errors to the form's `[data-cmnsd-error]` or the message area (`messages.js showError()`). Without JavaScript the markup must still do something sensible: render controls `hidden` and let the module show them.
