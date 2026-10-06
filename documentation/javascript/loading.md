# Loading and sections

Parts of a page that are filled in after it loads: a value that's slow to compute, or a section the viewer keeps closed. Both use the API's field endpoint and the same template the page would render itself, so the result looks the same either way.

## Deferred fields (fields.js)

A template renders an empty placeholder; cmnsd.js fills it once the page is ready:

```django
<span data-model="storyline" data-object-token="{{ storyline.token }}"
      data-field="get_reading_time" data-load-on-ready="true"></span>
```

| Attribute | Value |
|---|---|
| `data-load-on-ready` | Exactly `"true"` |
| `data-model` | The model's API name |
| `data-object-token` | The object's token - never the pk or slug |
| `data-field` | An `@api_field` on that model |

All placeholders for one object go in one request (`api/storyline/<token>/get_reading_time,get_summary/`). Each value is put in as returned: the API renders `<model>/functions/<field>.html` or `fields/<field>.html` when there is one, otherwise the escaped value.

There's no loading state and no retry. A missing field, a `null` or a failed request leaves the placeholder as it was - so leave it empty for things that may be absent, or put a fallback in it. Errors show in the console with `debug` on.

## The kill switch

`CMNSD_LOAD_ON_READY = False` turns deferred loading off site-wide, for when cmnsd.js is broken. Templates get it as `{{ load_on_ready }}`; a placeholder that follows the switch renders its content server-side instead:

```django
<span {% if load_on_ready %}data-model="storyline" data-object-token="{{ storyline.token }}"
      data-field="get_reading_time" data-load-on-ready="true"{% endif %}>
  {% if not load_on_ready %}{% include 'storyline/functions/get_reading_time.html' %}{% endif %}
</span>
```

## Collapsible sections (sections.js)

A page section the signed-in viewer can fold, remembered for the whole site: closing "storyline.chapters" closes it on every storyline page.

```django
{% include 'cmnsd/section.html' with key='storyline.chapters' title=title count=storyline.chapters.count
   body='storyline/functions/get_chapters.html' model='storyline' token=storyline.token field='get_chapters' %}
```

- **Open:** `body` is rendered as part of the page.
- **Closed:** only the header and count; the body is loaded through the API (`field`, which must be an `@api_field` rendering the same template as `body`) when it's opened. A closed section costs its count.
- **Empty** (count 0): a plain header, no toggle, nothing remembered - closing an empty section mustn't hide it everywhere else. With `empty_body` the body renders anyway, e.g. the form for a first comment.
- **Signed out:** a plain section, open and rendered - no toggle, nothing stored, no cookie.

Toggling posts `{key, open}` to `sectionStateUrl` ([cmnsd.js](readme.md)), stored in `Preferences.ui_state` (`ui/state.py`). The look is the project's CSS: `section.html` is markup only.

`count_list` and `count_items` on the include keep the count right after an action adds or removes an item ([Actions](actions.md)).
