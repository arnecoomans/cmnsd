# cmnsd.js

`cmnsd/static/cmnsd.js/` is the client-side half of the cmnsd API
(`cmnsd/views/api/`, design in `docs/cmnsd_api_design.md` in the
consuming project). It is plain ES modules with no build step and no
jQuery dependency.

It does two things:

- **Deferred field loading.** A template renders an empty placeholder,
  and cmnsd.js fills it from the API after the page has loaded.
- **Live list filtering.** A plain search form on a list page is
  upgraded to filter while typing, via the API's list endpoint. See
  [Live list filtering](#live-list-filtering).

For deferred loading: a template renders an empty placeholder, and
cmnsd.js fills it from the API after the page has loaded. Use this for values that are expensive to compute and not essential
to the first paint. `Person.get_relation_to_user` is the first example: it
walks the family tree for every page view, but the page is readable without
it.

| File | Role |
| --- | --- |
| `index.js` | Entry point: `init()` and `load()`, config, debug logging |
| `fields.js` | Finds placeholders, batches requests, fills elements |
| `list.js` | Upgrades list search forms to live filtering |
| `filter.js` | Filter pills: show/hide items in the browser, no request |
| `gallery.js` | Browse an image and its parts in place (‹ ›, arrow keys) |
| `sort.js` | Sort switch: reorder items in the browser by a data attribute |
| `actions.js` | Forms/buttons that call an API action and put the returned HTML in place |
| `csrf.js` | CSRF token for POSTs (meta tag, cookie fallback) |
| `sections.js` | Collapsible sections: POST open/closed to a project URL, load a closed section when opened |

## Setup

Loaded once, from the project's `base.html`, as a module:

```html
<script type="module">
  import cmnsd from "{% static 'cmnsd.js/index.js' %}";
  cmnsd.init({ apiRoot: '/api/', debug: {{ debug|yesno:'true,false' }} });
</script>
```

| Option | Default | Meaning |
| --- | --- | --- |
| `apiRoot` | `'/api/'` | Where `cmnsd.api_urls` is included in the project's `urls.py` |
| `debug` | `false` | Log requests, skipped elements and API errors to the console (`console.debug`, prefixed `[cmnsd]`) |

`{{ debug }}` is only set by Django's `debug` context processor when
`DEBUG` is on **and** the request comes from `INTERNAL_IPS`. Anywhere else
it's empty, so `yesno` gives `false`.

## Autoloading on page ready

Mark an element with the object and field it should show, plus
`data-load-on-ready="true"`:

```html
<span data-model="person"
      data-object-token="{{ person.token }}"
      data-field="get_relation_to_user"
      data-load-on-ready="true"></span>
```

| Attribute | Required | Value |
| --- | --- | --- |
| `data-load-on-ready` | yes | Exactly `"true"`, anything else is ignored |
| `data-model` | yes | The model's API registry name (`@api_model`), e.g. `person` |
| `data-object-token` | yes | The object's `token`. Not the pk, not the slug: the API identifies objects by token only |
| `data-field` | yes | One `@api_field` name on that model |

On `DOMContentLoaded` (or immediately, if the DOM is already parsed),
cmnsd.js:

1. Collects every element matching all four attributes. An element without
   `data-object-token` is skipped (logged in debug mode).
2. Groups them per object (`model` + `token`) and sends **one request per
   object**, with the field names comma-separated:
   `GET /api/person/ebc78e36c9e945ca9abb/get_relation_to_user,get_tags/`.
   Two elements asking for the same field of the same object share that
   request, and both get filled.
3. For each field in the response's `fields` object, sets the matching
   elements' `innerHTML` to the value, as-is.

Nothing else happens. There's no loading state, retry or error marker:

- The field is in the response with a value: it is inserted.
- The value is `null`, the field is missing (unknown or unexposed name), or
  the request failed: the element is left as it was.

Errors only surface in the console in debug mode. In `DEBUG`, the API
also queues an error message for unknown field names, but nothing displays
`messages` from the JS side yet.

Other `data-*` attributes on the same element (`data-object-id`,
`data-object-slug`, an `id`) are ignored. A `class` like `cmnsd_js` isn't
needed either; selection is by attribute.

### What the element ends up containing

The API's job is to return display-ready content. cmnsd.js doesn't format,
escape or wrap anything. What comes back depends on the server side:

- **The field has a template** (`<model>/functions/<field>.html` for a
  method, `<model>/fields/<field>.html` for a stored field): the rendered,
  minified template. So the markup for a lazily loaded field lives in the
  same function template an `{% include %}` would use. There is one source
  for it, not a separate JS-side rendering.
- **No template:** the plain value, HTML-escaped by the API
  (`conditional_escape`, so an intentional `mark_safe()` return survives).
  It's safe to insert, but it's only text. Anything that isn't a string
  (a queryset, a list) comes out as its `str()`, so give such fields a
  template.

### Placeholder content

Whatever is inside the element before loading stays visible until a value
arrives, and stays for good if none does. Leave it empty for things that
may legitimately be absent (a relation to an anonymous viewer), or put a
fallback in it:

```html
<span data-model="person" data-object-token="{{ person.token }}"
      data-field="get_relation_to_user" data-load-on-ready="true">
  {# empty: anonymous viewers and unrelated people get nothing #}
</span>
```

Don't put the `{% include %}` of the same function template inside the
placeholder unconditionally as a no-JS fallback. That renders the value
server-side and runs exactly the query you were trying to defer. Put it
behind the switch below instead.

## Turning deferred loading off

`CMNSD_LOAD_ON_READY` (setting, default `True`) is a site-wide kill switch
for when cmnsd.js is structurally broken. The `setting_data` context
processor exposes it to every template as `load_on_ready`. Each deferred
placeholder offers both paths:

```html
<span {% if load_on_ready %}data-model="person" data-object-token="{{ person.token }}"
      data-field="get_relation_to_user" data-load-on-ready="true"{% endif %}>
  {% if not load_on_ready %}
    {% include 'person/functions/get_relation_to_user.html' with person=person %}
  {% endif %}
</span>
```

- `True`: an empty placeholder, filled by cmnsd.js after page ready.
- `False`: no `data-*` attributes, so cmnsd.js finds nothing to load. The
  same function template renders server-side in the normal page request,
  so the page is complete without any JS.

The output is identical either way, because the API renders the same
template. Only the timing and the number of requests differ. A placeholder
written without the `{% if load_on_ready %}` branches doesn't follow the
switch: with it off, that field just stays empty.

## Loading content added later

Autoloading only scans once, at page ready. For HTML inserted later (a
modal, a tab, a fragment fetched some other way), run the same scan over
just that subtree:

```js
import cmnsd from "{% static 'cmnsd.js/index.js' %}";

container.innerHTML = fragment;
await cmnsd.load(container);   // defaults to document
```

`load()` returns a promise that resolves when every request for that
subtree has settled. It never rejects; failures are logged in debug mode.

Filled elements keep `data-load-on-ready="true"`, so calling `load()` on a
subtree that includes already-loaded elements fetches them again. Scope
it to the new content.

## Live list filtering

A list page renders its list server-side and wraps a plain GET search
form around it. Mark the form with the model and the element to update:

```html
<form method="get" action="{% url 'people:person_list' %}" role="search"
      {% if load_on_ready %}data-cmnsd-list="person" data-cmnsd-target="#person-list-results"{% endif %}>
  <input type="search" name="{{ search_character }}" value="{{ search_query }}">
</form>

<div id="person-list-results">
  {% include 'person/person_list.html' %}
</div>
```

| Attribute | Value |
| --- | --- |
| `data-cmnsd-list` | The model's API registry name, e.g. `person` |
| `data-cmnsd-target` | CSS selector of the element whose content is replaced |

On typing (250 ms debounce) or submit, cmnsd.js:

1. Builds a query string from the form's fields, dropping empty ones.
2. Calls `GET <apiRoot><model>/?<query>` (the API's list endpoint). A
   request still in flight is aborted, so a slow earlier response can't
   overwrite a newer one.
3. Replaces the target's `innerHTML` with the response's `html`, runs the
   deferred-field scan over it, binds any filter pills and sort switches
   in it, and updates the page URL (`history.replaceState`) so reloading
   or sharing shows the same list. Only the form's own fields change in
   the URL; other parameters (a filter pill's `?kind=`) are kept.

The search input must be named `{{ search_character }}` (the
`CMNSD_SEARCH_CHARACTER` setting, default `q`) - the API only treats that
parameter as free-text search. Other form fields are sent as filters and
only work for `@api_field`-exposed stored fields; see the API design
doc's Filtering section.

Without JS, or with `CMNSD_LOAD_ON_READY` off, the attributes aren't
rendered and the form submits normally: the page reloads with `?q=...`
and the view renders the filtered list server-side. The page and the
API both call `cmnsd.api.filtering.build_list()` and render the same
`<model>/<model>_list.html`, so both paths show the same result.

## Filter pills

For a small set of items that's already on the page (e.g. a person's
content cards), filtering needs no request. Mark the pill bar with the
container it filters, and each item with its value:

```html
<div data-cmnsd-filter="#person-content-grid" hidden>
  <button type="button" data-filter="" class="is-active" aria-pressed="true">All</button>
  <button type="button" data-filter="photo" aria-pressed="false">Photos</button>
</div>
<div id="person-content-grid">
  <a data-filter-value="photo" …>…</a>
</div>
```

Clicking a pill shows only the items whose `data-filter-value` matches
(`data-filter=""` shows all) and moves `.is-active` / `aria-pressed` to
it. Items are hidden with the `hidden` attribute. The bar is rendered
`hidden` and un-hidden by cmnsd.js, so without JS there are no dead
buttons and every item stays visible. Used by
`content/_content_grid.html`.

Add `data-cmnsd-filter-param="<name>"` to the bar to keep the choice in
the page address: a click sets `?<name>=<value>` (or removes it for
"all") with `history.replaceState`, without a reload, and on load a value
already in the address is applied - so a reload, back/forward or a
shared link keep the filter. An unknown value is ignored. It is not
stored anywhere else on purpose: a fresh visit starts on "all".

## Sort switch

For items already on the page, like filter pills. Mark the switch with the
container it sorts; each button names a key and a direction, each item
carries its value as `data-sort-<key>`:

```html
<div data-cmnsd-sort="#person-content-grid" hidden>
  <button type="button" data-sort-key="added" data-sort-direction="desc" class="is-active" aria-pressed="true">Recently added</button>
  <button type="button" data-sort-key="date" data-sort-direction="asc" aria-pressed="false">Chronologically</button>
</div>
<div id="person-content-grid">
  <a data-sort-added="2025-12-24T…" data-sort-date="1943-00-00" …>…</a>
</div>
```

Values are compared as text, so use sortable values (ISO dates;
`content_tags.date_sort_key` makes `1943-05-00` from a partial date). An
empty value always goes last, whatever the direction; ties keep their
order. Combines with filter pills (filtering only hides, sorting only
reorders). Hidden without JS, so the server's order stays. Used by the
person page's Content section.

**Remembering the choice:** add `data-cmnsd-sort-save="<key>"` to the
switch and pass `sortStateUrl` to `init()`; a click then POSTs `{key,
value}` (value = the button's `data-sort-key`). In fmly that's
`core:sort_state` (`/ui/sort/`), stored per signed-in user in
`Preferences.ui_state['sorts']` (`core/ui_state.py`, `get_sort` /
`set_sort`). The server renders the remembered order itself
(`Person.content_sort()` -> `get_visible_content()`) and marks that
button active, so the page opens in the right order without a visible
re-sort. Signed out: not stored, the default applies.

## Gallery

Browse a sequence of images in place - the content page uses it for an
item and its image parts (a book's cover and pages).

```html
<div data-cmnsd-gallery>
  <a href="…/file/" data-gallery-link><img src="…" data-gallery-image></a>
  <div class="content-gallery__nav" hidden>
    <button type="button" data-gallery-previous>‹</button>
    <span data-gallery-counter>1 / 7</span> · <a href="…" data-gallery-caption>…</a>
    <button type="button" data-gallery-next>›</button>
  </div>
  {{ gallery|json_script:"content-gallery-items" }}   {# [{title, src, file, page}, …] #}
</div>
<a href="…part page…" data-gallery-show="3">…thumbnail…</a>
```

‹ / › and the ← / → keys (not while typing) step through, wrapping round;
the image, its link (the original file), the counter and the caption
(the item's own page) follow. An optional `[data-gallery-open]` link
("Open page →") points to the shown item's own page and is hidden while
the first item - the page you're on - shows. Elements marked `data-gallery-show="<n>"`
show item n instead of navigating. Without JS: no buttons, the
thumbnails are plain links. A part's own page has server-side
"previous / next" links among its siblings as well.

## Collapsible sections

`sections.js` enhances `<details data-cmnsd-section="<key>">`. It's
generic; what gets remembered, where, and for whom is up to the project.

- **Toggling** POSTs `{key, open}` to `sectionStateUrl` (an `init()`
  option), with the CSRF token from `<meta name="csrf-token">` (falling
  back to the `csrftoken` cookie). Without `sectionStateUrl`, nothing is
  saved - sections just open and close natively.
- **Opening** a section whose body is marked `data-load-on-open="true"`
  (plus `data-model` / `data-object-token` / `data-field`) fills that body
  through the API, like a deferred field, then binds any filter pills in
  it. So a project can leave a closed section's body unrendered.

**In fmly** (project-specific, so in `core`, not cmnsd):

- `core/templates/core/section.html` renders the section:
  ```django
  {% include 'core/section.html' with key='person.content' title=title count=person|content_count:request
     body='person/functions/get_visible_content.html' model='person' token=person.token field='get_visible_content' %}
  ```
  Open: `body` is rendered. Closed: header + count only, body loaded via
  the API when opened. Count 0: a plain, muted header - no toggle, nothing
  recorded; with `empty_body` the body still renders (plain section, no
  toggle) - the person page's Comments uses that for signed-in users, so
  the first comment can be posted. `CMNSD_LOAD_ON_READY` off: every body
  rendered server-side.
- `core/ui_state.py` stores the state per section key for the whole site
  (closing `person.relationships` closes it on every person page) in
  `core.Preferences.ui_state`, for **signed-in users only**. Default: open.
- `core:section_state` (`/ui/section/`) is the endpoint `base.html` passes
  as `sectionStateUrl`.
- **Signed-out visitors** always get the default: a plain `<section>`,
  open and fully rendered - no toggle, nothing stored, no cookie (the
  endpoint answers 403; `base.html` renders the `csrf-token` meta tag for
  signed-in users only).
- `field` must be an `@api_field` whose function template is `body` - e.g.
  `Person.get_visible_content` / `person/functions/get_visible_content.html`
  (`people/models/SectionShorthand.py`).

## Actions

A form or button marked `data-cmnsd-action` POSTs to an `@api_action`
(`api/<model>/<token>/<action>/`, see the API design doc's Actions) and
puts the returned `html` in place:

```html
<form data-cmnsd-action="add_comment" data-model="content" data-object-token="{{ item.token }}"
      data-cmnsd-target="#comments-{{ item.token }}" data-cmnsd-insert="append">
  <textarea name="content"></textarea>
  <p data-cmnsd-error hidden></p>
  <button type="submit">Post</button>
</form>
<button type="button" data-cmnsd-action="delete_comment" data-model="comment" data-object-token="…"
        data-cmnsd-target="closest:.comment-row" data-cmnsd-insert="remove" data-cmnsd-confirm="Delete?">delete</button>
```

| Attribute | Meaning |
| --- | --- |
| `data-cmnsd-action`, `data-model`, `data-object-token` | which action on which object |
| `data-cmnsd-target` | a CSS selector, or `closest:<selector>` (an ancestor of the form/button) |
| `data-cmnsd-insert` | `append`, `prepend`, `replace`, `remove` |
| `data-cmnsd-confirm` | optional confirmation question |

A form sends its fields as JSON; a button sends nothing. Errors (`ok:
false`) go into the form's `[data-cmnsd-error]`, or an alert. After an
`append` the form is reset. Event delegation on the document: elements
added later (a new comment's own edit/delete buttons) work without
rebinding. The CSRF token comes from `<meta name="csrf-token">`
(`csrf.js`), which fmly's `base.html` renders for signed-in users.

## Not built yet

- **Load on visibility.** Loading when an element scrolls into view
  (`IntersectionObserver`) instead of at page ready. The natural shape is a
  second attribute value (`data-load-on-ready="visible"`, or a separate
  `data-load-on-visible`), feeding the same batching in `fields.js`.
- **Messages.** The API response carries `messages`, but nothing renders
  them yet (`templates/messages.html` is empty).
