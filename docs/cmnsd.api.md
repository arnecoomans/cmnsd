# cmnsd.api — AJAX Dispatch System

## Overview

`cmnsd.api` is a generic AJAX dispatch layer built on Django class-based views.
It translates URL params and JSON responses into model/field/function operations,
returning structured JSON payloads that cmnsd.js distributes into the DOM.

Mounted at `{% url 'cmnsd:dispatch' '<model>' %}` (e.g. `/api/locations/`).

---

## URL patterns

```
GET /api/<model>/                          → render model list
GET /api/<model>/<id>-<slug>/              → render single object
GET /api/<model>/<id>-<slug>/<field>/      → render field or function
```

Query params can also supply the object identifiers:
`?model=location&object_token=abc&object_slug=my-place&field=map_filters`

---

## Request lifecycle (`AjaxDispatch.dispatch`)

1. **_detect_model** — resolves `?model=` or URL segment to a Django model class
   via `meta_model`. Blocked by `AJAX_BLOCKED_MODELS` in settings.
2. **_detect_object** — looks up the object using ≥2 identifiers (id, slug, token).
   Applies `FilterMixin.filter()` for security-scoped queryset.
3. **_detect_fields** — splits `?field=` on commas; maps each name to either a
   `meta_field` (model field) or `meta_function` (@ajax_function method).
4. **get/post/patch/delete** calls `crud__read` / `crud__update` / `crud__delete`.

---

## Response format

```json
{
  "status": 200,
  "messages": [...],
  "payload": {
    "<field_name>": "<rendered HTML string>",
    "<function_name>": "<rendered HTML string>"
  }
}
```

Messages carry level (`info`, `warning`, `error`, `debug`) and a rendered HTML string.

---

## Template resolution (render_field)

For a field `name` on model `location` the dispatcher tries templates in order:

```
object/location_<field>.html
function/location/<field>.html    ← only for @ajax_function
function/location_<field>.html    ← only for @ajax_function
function/<field>.html             ← only for @ajax_function
field/location/<field>.html
field/location_<field>.html
field/<field>.html
```

Template context always includes:
- `request`, `field_name`, `field_value`, `<field_name>` (the resolved value)
- `format`, `model`, `obj`, `q` (search query char)
- `<model_name>` (the model instance)

---

## @ajax_function decorator

```python
from cmnsd.models.BaseMethods import ajax_function

@ajax_function
def map_filters(self):
    return ''   # return value becomes field_value in context; template does the work
```

Marks the method as AJAX-callable. The dispatcher checks `func.is_ajax_callable`.
`request` is available as `self.request` because `meta_object` sets it before calling.

Also available: `@ajax_login_required` (combines auth check + ajax_callable flag),
`@searchable_function` (marks method for FilterMixin `?method=true/false` filtering).

---

## Security

- `AJAX_BLOCKED_MODELS` list in settings blocks entire models.
- Object lookup requires ≥2 identifiers (prevents single-identifier enumeration).
- `FilterMixin` applies visibility/status scoping before passing queryset to `meta_object`.
- `SEARCH_BLOCKED_FIELDS` (and hardcoded: `password`, `token`, `secret_key`, `api_key`)
  block sensitive field names from being accessed.
