# Templatetags

Four `{% load %}`-able libraries under `cmnsd/templatetags/`.

## markdown

```django
{% load markdown %}
{{ body|markdown }}
```

Renders a markdown string to HTML via [python-markdown](https://python-markdown.github.io/),
then sanitizes it with [nh3](https://nh3.readthedocs.io/) before marking it
safe.

- **Extensions**: `settings.CMNSD_MARKDOWN_EXTENSIONS` (default:
  `['fenced_code', 'nl2br', 'tables']`). A single setting so both this filter
  and any future model-level markdown processing (e.g. a `Storyline` body
  extracting `[[kind:id]]` reference tokens) stay in sync.
- **Sanitization is the actual XSS boundary here** — python-markdown has no
  HTML sanitization of its own (`safe_mode` was removed in 3.0), so raw
  `<script>`/event-handler HTML written into a markdown source body would
  otherwise pass straight through to the rendered page. `nh3.clean()` strips
  it with a default allowlist, plus one addition: `<code>`'s `class`
  attribute is allowed (needed for `fenced_code`'s `language-xxx` class for
  syntax highlighting), but only tokens matching `language-xxx` — anything
  else riding along on that attribute is stripped, so it can't be used to
  smuggle an arbitrary extra class onto the element.

## query_filters

```django
{% load query_filters %}
```

| Name | Kind | Signature | Purpose |
|---|---|---|---|
| `tojson` | filter | `value\|tojson` | Serialize a value to JSON, safe to drop into an HTML attribute |
| `update_query_params` | simple_tag | `update_query_params request add=… remove=… to=… replace=… clear=…` | Add/remove/replace/clear one query param on the current URL, keeping the rest intact |
| `copy_query_params` | simple_tag | `copy_query_params request prepend=…` | Copy the current query string, optionally prefixing every key |

**`tojson`** uses `DjangoJSONEncoder`, so it handles `UUID`/`Decimal`/
`date`/`datetime` — types that plain `json.dumps()` chokes on but that
Django template contexts hold constantly (model PKs, prices, timestamps).
It's deliberately **not** marked safe: Django's own autoescaping
HTML-entity-encodes the quotes and angle brackets in the JSON output, which
is exactly what keeps it safe to interpolate into an attribute:

```django
<div data-items="{{ items|tojson }}"></div>
```

If you ever need it inside an inline `<script>` block instead, use Django's
own built-in `{{ value|json_script:"id" }}` — it renders its own
`<script type="application/json">` tag with the right escaping for *that*
context, which is different from the attribute case above.

**`update_query_params`** stores multi-value params joined with `__and__`
(not a plain comma, to avoid colliding with values that legitimately
contain a comma), and reads back both `__and__` and comma-joined values for
backward compatibility with older links. `to` is required for every
modification (`add`/`remove`/`replace`/`clear`); omitting it while also
passing one of those raises `ValueError`.

```django
<a href="{% url 'list' %}{% update_query_params request add='family' to='tags' %}">Add "family" tag</a>
<a href="{% url 'list' %}{% update_query_params request remove='family' to='tags' %}">Remove it</a>
<a href="{% url 'list' %}{% update_query_params request replace='concept' to='status' %}">Replace status</a>
<a href="{% url 'list' %}{% update_query_params request clear='status' %}">Clear status</a>
```

**`copy_query_params`** preserves multi-value keys correctly (e.g.
`?tag=a&tag=b`) using `request.GET.lists()`. `prepend` is concatenated
directly onto each key, so include your own separator: `prepend='sub_'`,
not `prepend='sub'`.

## queryset_filters

```django
{% load queryset_filters %}
```

| Name | Signature | Purpose |
|---|---|---|
| `filter_by_status` | `qs\|filter_by_status:request` | Delegates to `StatusMixin.filter_status()` |
| `filter_by_visibility` | `qs\|filter_by_visibility:request` | Delegates to `VisibilityMixin.filter_visibility()` |
| `filter_by_user` | `qs\|filter_by_user:user` | Restrict to objects owned by `user`, if authenticated |
| `without` | `qs_or_list\|without:obj_or_qs` | Exclude one object, or every object in a queryset, from a queryset or list |
| `match_queryset` | `qs\|match_queryset:obj_or_qs` | Restrict to one object, or every object in a queryset |

`filter_by_status` and `filter_by_visibility` are intentionally thin — they
just call the mixin classmethod on `queryset.model`. The filtering rules
themselves live in exactly one place (see [models.md](models.md) —
`StatusMixin`/`VisibilityMixin`), not duplicated here. A template-level
reimplementation is how a prior version of this filter drifted from
`VisibilityMixin.filter_visibility` and silently lost a needed
`.distinct()` — don't reintroduce a second implementation of either rule.

`without`/`match_queryset` both accept either a single model instance or a
`QuerySet` as the comparison object, and both work against a `QuerySet` or
a plain `list` on the left-hand side.

## text_filters

```django
{% load text_filters %}
```

| Name | Kind | Signature | Purpose |
|---|---|---|---|
| `replace` | filter | `value\|replace:"what\|to"` | Replace the first `what` with `to`, packed into one pipe-separated arg |
| `highlight` | filter | `value\|highlight:query` | Wrap the (case-insensitive) match of `query` in `CMNSD_HIGHLIGHT_TAG` (default `<mark>`) |
| `highlight_search` | block tag | `{% highlight_search query %}…{% endhighlight_search %}` | Mark each whitespace-separated term of `query` in the rendered block's visible text, as `<mark class="search-hit">` |
| `str_replace` | simple_tag | `str_replace value what to` | Same substitution as `replace`, with `what`/`to` as separate args |
| `without_value` | filter | `list\|without_value:value` | Exclude every list item equal to `value` |
| `prepend` | filter | `value\|prepend:"prefix"` | Prepend a string |
| `get_item` | filter | `dict\|get_item:key` | Look up a dict value by a *variable* key |

A few of these overlap with Django builtins — know which one you're
reaching for:

- `replace` has no Django built-in equivalent (a general find-and-replace
  filter isn't in Django core). Its `"what|to"` packing breaks if `what` or
  `to` contains a literal `|` — use `str_replace` instead when either value
  might.
- `str_replace` exists specifically for that case: `objreplace`'s original
  name, kept as a separate tool alongside `replace` rather than replacing
  it, since a `simple_tag` with explicit args doesn't have the pipe-packing
  fragility.
- `highlight`'s `value` and `query` are both HTML-escaped *before* the
  highlight tag is injected, and only then is the whole result marked safe —
  so text already in `value` (e.g. an ampersand in a name) can't be used to
  break out of the injected tag, only the tag itself renders as HTML.
- `highlight_search` vs `highlight`: `highlight` takes a plain value and
  escapes it, so it can't run over HTML (it would escape existing tags into
  visible text). `highlight_search` renders its block first and marks
  terms only in the text *between* tags and entities, so it's safe around
  an `{% include %}` that already contains links or `|highlight` marks, and
  the two can overlap. A blank or missing query leaves the block unchanged.
  Used around the name in `people/_person_row.html` with the list's
  `search_query`, so a search shows why a row matched (Di**eric**xdr).
  `mark.search-hit` is styled apart from a plain `mark` in `base.css`.
- For "remove all occurrences of a substring", use Django's built-in
  `{{ value|cut:"x" }}` — it already does exactly that. `without_value` is
  for something different: excluding matching *items* from a list, not
  substrings from a string.
- For prepending, Django's built-in `add` filter already does it in
  reverse argument order: `{{ "Mr. "|add:name }}` ≡
  `{{ name|prepend:"Mr. " }}`. `prepend` reads in the more natural
  subject-first order, which is the only reason to reach for it over `add`.
- `get_item` is not redundant with anything built in — Django's
  `{{ dict.key }}` dot-lookup only works with a *literal* key written in
  the template; it can't look up by the value of a context variable
  (`{{ dict.some_variable }}` doesn't do a variable-key lookup). `get_item`
  is the standard workaround, and comes up often inside `{% for %}` loops
  keying into a lookup dict.
