# Lists

Three ways to narrow or order a list. A live search asks the API; filter pills and the sort switch only rearrange items already on the page.

## Live search (list.js)

A list page renders its list server-side, inside a plain GET search form. Mark the form with the model and the element to update:

```django
<form method="get" role="search"
      {% if load_on_ready %}data-cmnsd-list="storyline" data-cmnsd-target="#storyline-results"{% endif %}>
  <input type="search" name="{{ search_character }}" value="{{ search_query }}">
</form>
<div id="storyline-results">{% include 'storyline/storyline_list.html' %}</div>
```

While typing (debounced) or on submit, it calls `api/storyline/?q=...` with the form's non-empty fields, replaces the target's content with the response's `html`, enhances it, and updates the address bar, so a reload or a shared link shows the same list. A request still running is aborted: a slow answer can't overwrite a newer one.

- The search field is named `{{ search_character }}` (`CMNSD_SEARCH_CHARACTER`, default `q`).
- Other fields filter only on stored `@api_field` fields ([The API](../api.md)).
- The view and the API both call `api.filtering.build_list()` and render `<model>/<model>_list.html`, so without JavaScript the form submits and the page shows the same result.

## Filter pills (filter.js)

For items already on the page - no request:

```html
<div data-cmnsd-filter="#story-cards" data-cmnsd-filter-param="kind" hidden>
  <button type="button" data-filter="" class="is-active" aria-pressed="true">All</button>
  <button type="button" data-filter="photo" aria-pressed="false">Photos</button>
</div>
<div id="story-cards">
  <a data-filter-value="photo" ...>...</a>
</div>
```

A pill shows the items whose `data-filter-value` matches (`""` shows all) and hides the rest with `hidden`. The bar is rendered `hidden` and shown by cmnsd.js, so without JavaScript there are no dead buttons. With `data-cmnsd-filter-param` the choice is kept in the address (`?kind=photo`), not stored anywhere else: a new visit starts on "all".

## Sort switch (sort.js)

Also for items already on the page. Each button names a key and a direction; each item carries its value as `data-sort-<key>`:

```html
<div data-cmnsd-sort="#story-cards" data-cmnsd-sort-save="storyline.cards" hidden>
  <button type="button" data-sort-key="added" data-sort-direction="desc" class="is-active" aria-pressed="true">Recently added</button>
  <button type="button" data-sort-key="date" data-sort-direction="asc" aria-pressed="false">By date</button>
</div>
<a data-sort-added="2026-04-01T10:00" data-sort-date="1943-05-00" ...>...</a>
```

- Values compare as text: use sortable values, such as ISO dates (`1943-05-00` for a partial date). An empty value goes last either way; ties keep their order.
- Works with filter pills: filtering hides, sorting reorders.
- **Remembered** with `data-cmnsd-sort-save="<key>"` and `sortStateUrl` in `init()`: a choice is posted and stored per signed-in user. The view renders that order itself - `get_sort(request, key, default, allowed)` in `ui/state.py` - and marks the button active, so the page opens in the right order without a visible re-sort.

## A-Z index

Not JavaScript, but often next to a list: `{% with index=storylines|group_by_initial:'title' %}` gives letters with counts and the groups under them, accents folded ([Templates and tags](../templates.md)).
