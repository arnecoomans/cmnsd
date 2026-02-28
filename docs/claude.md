# Working with Claude on cmnsd

This document helps Claude understand the `cmnsd` app — a reusable, standalone Django app that provides model-agnostic AJAX views, a filtering system, and a custom JavaScript framework.

---

## What cmnsd Is

`cmnsd` is a **drop-in Django app** that:

1. Provides a **generic AJAX dispatch system** that exposes any registered Django model over HTTP without hardcoding models into views
2. Ships a **custom JavaScript framework** (`cmnsd.js`) for consuming those AJAX endpoints from templates
3. Locally hosts **Bootstrap 5**, **Bootstrap Icons**, **jQuery**, and **jQuery UI** (no CDN dependency)
4. Provides **reusable mixins** for filtering, request parsing, message management, and JSON response formatting
5. Offers **abstract base models** (`BaseModel`, `VisibilityModel`, `TagModel`) for consistent field conventions across apps

The AJAX system is the core feature: it dynamically resolves models by name, looks up objects by identifier, and reads/updates/deletes fields — all driven by request parameters, with no per-model configuration needed.

---

## Project Structure

```
cmnsd/
├── apps.py                          # AppConfig, registers system checks on ready
├── urls.py                          # AJAX URL patterns
├── checks.py                        # System checks validating required settings
├── context_processors.py            # Template context variables with fallbacks
├── admin.py                         # ReadOnlyAdmin base class
├── Readme.md                        # Main app documentation
├── models/
│   ├── BaseModel.py                 # Abstract: token, status, timestamps, user
│   ├── VisibilityModel.py           # Abstract: visibility field + properties
│   ├── TagModel.py                  # Abstract: hierarchical tag with slug, parent
│   ├── MultiSiteBaseModel.py        # Abstract: Django sites framework support
│   ├── cmnsd_basemodel.py           # Combined BaseModel + VisibilityModel
│   ├── cmnsd_basemethod.py          # Decorators: @ajax_function, @searchable_function
│   ├── Category.py                  # Concrete: hierarchical category
│   ├── Comment.py                   # Concrete: generic comment (GenericForeignKey)
│   └── Tag.py                       # Concrete: hierarchical tag
├── mixins/
│   ├── RequestMixin.py              # Extract values from GET/POST/JSON/headers/kwargs
│   ├── FilterMixin.py               # Unified filtering (access, status, visibility, search)
│   ├── MessagesMixin.py             # Message container + view mixin
│   └── ResponseMixin.py             # JSON response builder + template renderer
├── views/
│   ├── ajax_dispatch.py             # Main AjaxDispatch view (entry point)
│   ├── ajax__crud_read.py           # GET: read fields/object/model
│   ├── ajax__crud_update.py         # POST/PATCH: update fields
│   ├── ajax__crud_delete.py         # DELETE: soft or hard delete
│   ├── ajax__crud__util.py          # Shared CRUD utilities
│   ├── ajax_utils_meta_model.py     # meta_model: wraps Django model class
│   ├── ajax_utils_meta_object.py    # meta_object: wraps model instance
│   ├── ajax_utils_meta_field.py     # meta_field: wraps model field with update logic
│   └── ajax_utils_meta_function.py  # meta_function: wraps @ajax_function methods
├── templatetags/
│   ├── cmnsd.py                     # portrait_crop inclusion tag
│   ├── text_filters.py              # String manipulation (replace, highlight, split, …)
│   ├── math_filters.py              # Math filters (div, mul, sub, addf, floatfmt, …)
│   ├── humanize_date.py             # Relative date formatting, age calculation
│   ├── markdown.py                  # Markdown rendering filter
│   ├── query_filters.py             # URL query parameter manipulation
│   └── queryset_filters.py          # Queryset filtering in templates
├── static/
│   ├── css/
│   │   ├── bootstrap-5.0.2/         # Bootstrap CSS (locally hosted)
│   │   ├── bootstrap-icons-1.13.1/  # Bootstrap Icons (locally hosted)
│   │   └── cmnsd/                   # Custom: cmnsd.css, branding, cropper, messages, …
│   └── js/
│       ├── bootstrap-5.0.2/         # Bootstrap JS (locally hosted)
│       ├── jquery-3.7.1/            # jQuery (locally hosted)
│       ├── jquery-ui-1.14.1/        # jQuery UI (locally hosted)
│       └── cmnsd/                   # Custom JS framework (see below)
├── resources/
│   ├── update.py / update.sh        # Deployment automation (pull, migrate, collectstatic)
│   └── requirements.txt             # Python dependencies
└── docs/
    ├── claude.md                    # This file
    ├── add_basemodel.md
    └── templatetags.md
```

---

## The AJAX Dispatch System

This is the heart of cmnsd. A single view (`AjaxDispatch`) handles CRUD for **any** Django model without per-model view code.

### How It Works

A request arrives at a URL like `/json/<model>/` or `/json/<model>/<id>-<slug>/`. `AjaxDispatch` then:

1. **Detects the model** from the `model` request parameter using `meta_model` (resolves by class name or verbose name)
2. **Detects the object** from identifier parameters (`object_id`, `object_slug`, `object_token` — requires at least two) using `meta_object`
3. **Detects requested fields** from the `field` parameter using `meta_field`
4. **Dispatches** to the appropriate CRUD handler: `GET` → read, `POST`/`PATCH` → update, `DELETE` → delete

### URL Patterns

```python
# cmnsd/urls.py
urlpatterns = [
    path('json/<str:model>/', AjaxDispatch.as_view(), name='ajax_dispatch'),
    path('json/<str:model>/<str:object_id>-<str:object_slug>/', AjaxDispatch.as_view(), name='ajax_dispatch_object'),
    # ... additional identifier patterns
]
```

Mounted in the host project at `/json/` by convention.

### Meta Wrappers

| Class | File | Purpose |
|---|---|---|
| `meta_model` | `ajax_utils_meta_model.py` | Wraps a Django model class. Resolves by name, checks field/function existence, enforces `AJAX_BLOCKED_MODELS`. |
| `meta_object` | `ajax_utils_meta_object.py` | Wraps a model instance. Handles multi-identifier lookup (id+slug+token), change tracking, commit. |
| `meta_field` | `ajax_utils_meta_field.py` | Wraps a field on an instance. Type detection (simple/FK/related/bool), `value()`, `update_simple()`, `update_foreign_key()`, `update_related()`. Enforces `AJAX_PROTECTED_FIELDS` and `AJAX_RESTRICTED_FIELDS`. |
| `meta_function` | `ajax_utils_meta_function.py` | Wraps an `@ajax_function`-decorated method. Resolves required args from request, calls and returns result. |

### CRUD Behaviour

**Read (GET):**
- If `field` is set → renders each field via `render_field()` (template-based with fallback)
- If object is found but no field → renders full object via `render_obj()`
- If no object → renders model list via `render_model()`

**Update (POST/PATCH):**
- Parses request body into structured payload
- Determines update type per field: simple / foreign key / related (M2M)
- Can create new related objects if model is in `AJAX_ALLOW_FK_CREATION_MODELS` or `AJAX_ALLOW_RELATED_CREATION_MODELS`
- Logs all changes to `meta_object.get_changes()`

**Delete (DELETE):**
- Soft delete: sets `status = 'x'` if model has a `status` field
- Hard delete: calls `.delete()` if no `status` field

### JSON Response Structure

```json
{
  "status": 200,
  "messages": [{"level": "info", "message": "...", "count": 1, "rendered": "<html>"}],
  "payload": { ... },
  "__meta": { ... }  // staff users only: model, object, fields, request info
}
```

---

## Mixins

All mixins are in `cmnsd/mixins/` and exported from `cmnsd/mixins/__init__.py`.

### RequestMixin

Extracts values from multiple request sources.

```python
from cmnsd.mixins import RequestMixin

class MyView(RequestMixin, View):
    def get(self, request, *args, **kwargs):
        value = self.get_value_from_request('my_param')  # checks GET, POST, JSON, headers, kwargs
        keys = self.get_keys_from_request()
        body = self.json_body  # cached parsed JSON
```

**Key method:** `get_value_from_request(key, default=None, sources=None, silent=False)`
- `sources`: list of `'get'`, `'post'`, `'json'`, `'headers'`, `'kwargs'`
- `silent=True`: suppresses errors, returns `None`
- Default source order from `AJAX_DEFAULT_DATA_SOURCES` setting

### FilterMixin

Single `filter()` call applies access control, status, visibility, and search.

```python
from cmnsd.mixins import FilterMixin

class MyView(FilterMixin, View):
    def get(self, request, *args, **kwargs):
        qs = MyModel.objects.all()
        filtered_qs = self.filter(qs)
        # Applies: access restriction, status=p, visibility, search
```

**`filter(queryset, request=None, suppress_search=False, allow_staff=False, mapping={})`**

- `mapping`: maps URL params to queryset filters (e.g. `{'country': 'region__parent__parent__slug'}`)
- `suppress_search`: skips free-text search (used when filtering for security without user input)
- Search supports `&&` (AND) and `||` (OR) operators in the `?q=` parameter

**Sub-mixins (not used directly):**
- `FilterAccessMixin` — user-ownership restriction via `RESTRICT_READ_ACCESS`
- `FilterStatusVisibilityMixin` — filters `status='p'`, visibility by user relationship
- `FilterSearchMixin` — field search, free-text search, `?exclude=` param

### MessagesMixin

Two classes in `cmnsd/mixins/MessagesMixin.py`:

- **`MessagesMixin`** — the message container (stores, deduplicates, formats messages)
- **`MessageMixin`** — the view mixin; initialises `self.messages = MessagesMixin()` in `__init__`

Use `MessageMixin` as the view base class:

```python
from cmnsd.mixins import MessagesMixin  # the container class

class MyView(MessageMixin, View):  # MessageMixin sets up self.messages
    def get(self, request, *args, **kwargs):
        self.messages.add("Something happened", level="info")
        self.messages.add("Debug detail", level="debug")  # hidden unless DEBUG + staff
```

**Important naming:** `MessagesMixin` ≠ `MessageMixin`. The container is `MessagesMixin`; the view mixin is `MessageMixin`.

### ResponseMixin

Builds structured JSON responses and renders fields/objects via Django templates.

```python
from cmnsd.mixins import ResponseMixin

class MyView(ResponseMixin, View):
    def get(self, request, *args, **kwargs):
        return self.return_response(payload={'key': 'value'})
        # or with status:
        return self.return_response(status=400)
```

**Template rendering fallback chain** (for `render_field`):
1. `object/<model>_<field>.<format>`
2. `field/<model>/<field>.<format>`
3. `field/<model>_<field>.<format>`
4. `field/<field>.<format>`
5. Falls back to `str(value)` if no template found

---

## Abstract Base Models

### BaseModel

All models in apps using cmnsd should inherit from `BaseModel`:

```python
from cmnsd.models import BaseModel

class MyModel(BaseModel):
    name = models.CharField(max_length=200)
    # Automatically available:
    # token        — unique public ID (10-20 chars, URL-safe, auto-generated)
    # status       — 'c'=concept, 'p'=published, 'r'=revoked, 'x'=deleted
    # date_created — auto timestamp
    # date_modified — auto timestamp
    # user         — FK to AUTH_USER_MODEL (nullable)
```

**Key methods/properties:**
- `ajax_slug` → `"{id}-{slug}"` or `"{id}-{token}"` (for AJAX URLs)
- `get_ajax_url()` → full AJAX endpoint URL
- `get_optimized_queryset()` → override to return select_related/prefetch_related queryset
- `get_searchable_fields()` → override to expose fields for free-text search

### VisibilityModel

Add visibility control to any model:

```python
from cmnsd.models import BaseModel, VisibilityModel

class MyModel(BaseModel, VisibilityModel):
    # visibility — 'p'=public, 'c'=community, 'f'=family, 'q'=private (default: 'c')
    # is_public, is_community, is_family, is_private — bool properties
```

### TagModel (Abstract)

For hierarchical tagging systems:

```python
from cmnsd.models import TagModel

class MyTag(TagModel):
    # slug, name, parent (self-ref FK), description
    # display_name() → "parent: child" format
    # Unique constraint: name per parent
```

### cmnsd_basemethod decorators

Mark model methods as callable from AJAX:

```python
from cmnsd.models.cmnsd_basemethod import ajax_function, searchable_function

class MyModel(BaseModel):
    @ajax_function
    def get_summary(self, request=None):
        """Called by AjaxDispatch when field='get_summary'"""
        return {'summary': self.name}

    @searchable_function
    def full_text(self):
        """Included in free-text search"""
        return f"{self.name} {self.description}"
```

---

## JavaScript Framework (cmnsd.js)

The custom JS framework in `static/js/cmnsd/` provides client-side integration with the AJAX endpoints.

### Files

| File | Purpose |
|---|---|
| `index.js` | Entry point, initialises cmnsd |
| `core.js` | Core functionality and configuration |
| `http.js` | HTTP request utilities (fetch wrapper) |
| `csrf.js` | CSRF token extraction and injection |
| `messages.js` | Display server messages in UI |
| `actions.js` | Action button handlers |
| `dom.js` | DOM utilities |
| `loader.js` | Dynamic content loading |
| `autosuggest.js` | Autocomplete/typeahead implementation |
| `autosuggest-extension.js` | Extended autocomplete behaviour |
| `cropper.js` | Image cropping interface |

### Static Dependencies (locally hosted, no CDN)

| Library | Version | Path |
|---|---|---|
| Bootstrap CSS | 5.0.2 | `static/css/bootstrap-5.0.2/` |
| Bootstrap Icons | 1.13.1 | `static/css/bootstrap-icons-1.13.1/` |
| Bootstrap JS | 5.0.2 | `static/js/bootstrap-5.0.2/` |
| jQuery | 3.7.1 | `static/js/jquery-3.7.1/` |
| jQuery UI | 1.14.1 | `static/js/jquery-ui-1.14.1/` |

**Never add CDN links for these libraries** — they are intentionally self-hosted.

---

## Template Tags

Load in templates with `{% load <taglib> %}`.

### `cmnsd`
```django
{% load cmnsd %}
{% portrait_crop image %}  {# Responsive portrait crop with cropper.html #}
```

### `text_filters`
```django
{% load text_filters %}
{{ value|replace:"old|new" }}
{{ value|highlight:query }}
{{ value|split:"," }}
{{ value|whatsapp_number }}
{{ value|remove:"unwanted" }}
{{ value|prepend:"prefix" }}
```

### `math_filters`
```django
{% load math_filters %}
{{ value|div:2 }}
{{ value|mul:3 }}
{{ value|sub:1 }}
{{ value|addf:0.5 }}
{{ value|floatfmt:2 }}
{{ value|floatdot }}
```

### `humanize_date`
```django
{% load humanize_date %}
{{ date_value|humanize_date }}        {# "3 days ago" / "in 2 weeks" #}
{{ event_date|calc_age:birth_date }}  {# Age in years #}
```

### `markdown`
```django
{% load markdown %}
{{ content|markdown }}  {# Renders Markdown: fenced code, nl2br, tables #}
```

### `query_filters`
```django
{% load query_filters %}
{% update_query_params request add="key=value" remove="old_key" %}
{% copy_query_params request %}
```

### `queryset_filters`
```django
{% load queryset_filters %}
{% filter_by_status queryset as published %}
{% filter_by_visibility queryset user as visible %}
{% filter_by_user queryset user as owned %}
{% without queryset object as filtered %}
{% match_queryset queryset object as matched %}
```

---

## Required Settings

`checks.py` validates these on startup. Missing settings raise system check errors.

```python
# cmpng/settings.py

# Model defaults
DEFAULT_MODEL_STATUS = 'p'       # Default status for new objects ('c', 'p', 'r', 'x')
DEFAULT_MODEL_VISIBILITY = 'c'   # Default visibility ('p', 'c', 'f', 'q')

# Site metadata (used by context_processors.py)
SITE_NAME = 'My Project'
META_DESCRIPTION = 'Short site description'

# Search
SEARCH_QUERY_CHARACTER = 'q'       # URL param for free-text search
SEARCH_EXCLUDE_CHARACTER = 'exclude'
SEARCH_MIN_LENGTH = 2              # Minimum query length
SEARCH_BLOCKED_FIELDS = []         # Fields not searchable (in addition to 'password')

# AJAX system
AJAX_DEFAULT_DATA_SOURCES = ['get', 'post', 'json', 'kwargs']
AJAX_RENDER_REMOVE_NEWLINES = False
AJAX_PROTECTED_FIELDS = ['password', 'token', 'id']   # Never editable via AJAX
AJAX_RESTRICTED_FIELDS = []                             # Staff-only fields
AJAX_BLOCKED_MODELS = []                                # Models blocked from AJAX access
AJAX_IGNORE_CHANGE_FIELDS = []                          # Fields excluded from change log
AJAX_ALLOW_FK_CREATION_MODELS = []                      # Models where FK objects can be created
AJAX_ALLOW_RELATED_CREATION_MODELS = []                 # Models where M2M objects can be created
AJAX_MAX_DEPTH_RECURSION = 3                            # Max depth for nested object creation
AJAX_MODES = ['editable', 'add']                        # Supported AJAX modes
```

---

## Installing cmnsd in a Django Project

```python
# settings.py
INSTALLED_APPS = [
    ...
    'cmnsd',
]

TEMPLATES = [{
    'OPTIONS': {
        'builtins': [
            'cmnsd.templatetags.cmnsd',
            'cmnsd.templatetags.text_filters',
            'cmnsd.templatetags.math_filters',
            'cmnsd.templatetags.humanize_date',
            'cmnsd.templatetags.markdown',
            'cmnsd.templatetags.query_filters',
            'cmnsd.templatetags.queryset_filters',
        ],
    },
}]

CONTEXT_PROCESSORS = [
    ...
    'cmnsd.context_processors.cmnsd',
]
```

```python
# urls.py
urlpatterns = [
    path('json/', include('cmnsd.urls')),
    ...
]
```

---

## Using AJAX from a Template

The typical pattern: a template uses `data-` attributes on HTML elements that `cmnsd.js` picks up to make AJAX calls.

```html
<!-- Load cmnsd.js -->
<script src="{% static 'js/cmnsd/index.js' %}"></script>

<!-- Example: editable field -->
<span data-model="location"
      data-object-id="{{ location.id }}"
      data-object-slug="{{ location.slug }}"
      data-object-token="{{ location.token }}"
      data-field="name">
  {{ location.name }}
</span>
```

cmnsd.js translates this into a request to `/json/location/<id>-<slug>/` with `field=name`.

---

## Extending the AJAX System

### Make a model field accessible via AJAX

1. Inherit from `BaseModel` (provides `ajax_slug`, `get_ajax_url`, `token`)
2. Add to `ajax_fields` list on the model (documents available fields):

```python
class MyModel(BaseModel):
    ajax_fields = ['name', 'description', 'status']
    name = models.CharField(max_length=200)
```

### Make a model method callable via AJAX

```python
from cmnsd.models.cmnsd_basemethod import ajax_function

class MyModel(BaseModel):
    @ajax_function
    def render_card(self, request=None):
        """Available as field='render_card' in AJAX requests"""
        return {'html': '...'}
```

### Expose free-text search fields

```python
class MyModel(BaseModel):
    @classmethod
    def get_searchable_fields(cls):
        return ['name', 'description', 'user__username']
```

### Expose an optimized queryset

```python
class MyModel(BaseModel):
    @classmethod
    def get_optimized_queryset(cls):
        return cls.objects.select_related('user').prefetch_related('tags')
```

---

## Security Model

- **`AJAX_PROTECTED_FIELDS`**: Fields that can never be read or updated via AJAX (always includes `password`, `token`, `id`)
- **`AJAX_RESTRICTED_FIELDS`**: Fields only accessible to staff users
- **`AJAX_BLOCKED_MODELS`**: Model names that the AJAX system will refuse to resolve
- **Object lookup requires 2+ identifiers**: id+slug, id+token, or slug+token — prevents guessing
- **`FilterMixin` enforces visibility**: Anonymous users only see `visibility='p'`; community users see `'c'`; family sees `'f'`; owners see `'q'`
- **CSRF protection**: `csrf.js` handles token injection for all AJAX requests

---

## Common Gotchas

### 1. `MessagesMixin` vs `MessageMixin`

```python
# ❌ Wrong - MessagesMixin is the container, not the view mixin
class MyView(MessagesMixin, View):
    pass

# ✅ Correct - MessageMixin (no 's') is the view mixin
class MyView(MessageMixin, View):
    def get(self, request, *args, **kwargs):
        self.messages.add("Hello", "info")  # self.messages is a MessagesMixin instance
```

### 2. Importing mixins from the module instead of the class

```python
# ❌ Wrong - imports the module object (cmnsd/mixins/MessagesMixin.py), not the class
from cmnsd.mixins import MessagesMixin  # This is the class — OK since __init__.py exports it
# But if __init__.py is missing an export, you get the module not the class → metaclass conflict

# ✅ Always ensure __init__.py exports classes explicitly:
# from .MessagesMixin import MessagesMixin, MessageMixin
```

### 3. Object lookup requires two identifiers

```python
# ❌ Wrong - only one identifier, AJAX will not resolve the object
GET /json/location/?model=location&object_id=5

# ✅ Correct - two or more identifiers
GET /json/location/?model=location&object_id=5&object_slug=camping-paradise
```

### 4. CDN links for Bootstrap/jQuery

```html
<!-- ❌ Never do this - all static libs are self-hosted -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5/dist/css/bootstrap.min.css">

<!-- ✅ Use local static files -->
<link href="{% static 'css/bootstrap-5.0.2/bootstrap.min.css' %}">
```

### 5. `@ajax_function` for custom AJAX methods

```python
# ❌ Wrong - regular method, not reachable from AjaxDispatch
def my_method(self):
    return {'data': 'value'}

# ✅ Correct - decorated, reachable as field='my_method'
@ajax_function
def my_method(self, request=None):
    return {'data': 'value'}
```

---

## Dependencies (requirements.txt)

```
Django >= 5.1.0
Pillow >= 11.0.0           # Image handling
pillow-heif >= 0.21.0      # HEIC/HEIF image support
gunicorn >= 23.0.0         # WSGI server
geopy >= 2.4.1             # Geocoding + distance
googlemaps >= 4.10.0       # Google Maps API
Markdown >= 3.7            # Markdown rendering (templatetag)
django-sendfile2 >= 0.7.0  # Secure file downloads
```

---

## Current State

- ✅ AJAX dispatch system (read, update, delete)
- ✅ Meta wrappers (meta_model, meta_object, meta_field, meta_function)
- ✅ All mixins (Request, Filter, Messages, Response)
- ✅ Abstract base models (BaseModel, VisibilityModel, TagModel)
- ✅ Concrete models (Category, Comment, Tag)
- ✅ Full template tag library (7 tag modules)
- ✅ cmnsd.js framework with Bootstrap/jQuery self-hosted
- ✅ System checks for required settings
- ✅ Deployment scripts (update.py / update.sh)
