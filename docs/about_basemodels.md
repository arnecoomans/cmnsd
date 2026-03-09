# cmnsd Base Models

Reference for the abstract base models provided by the `cmnsd` app. All project models should inherit from these to get consistent fields, behaviours, and AJAX dispatch compatibility.

---

## BaseModel

**File:** `cmnsd/models/BaseModel.py`

Abstract base for every model in the project. Provides identity, lifecycle status, timestamps, and ownership.

### Fields

| Field | Type | Notes |
|---|---|---|
| `token` | `CharField(20)` | Auto-generated 10-char URL-safe public ID. Unique. Never shown in admin. |
| `status` | `CharField(1)` | `'c'` concept, `'p'` published, `'r'` revoked, `'x'` deleted. Default from `DEFAULT_MODEL_STATUS` setting. |
| `date_created` | `DateTimeField` | Set on creation, never updated. |
| `date_modified` | `DateTimeField` | Updated on every save. |
| `user` | `ForeignKey(User)` | Owner/creator. Nullable. `on_delete=SET_NULL`. |

### Methods

**`save()`** — Auto-generates a unique `token` if one is not already set. Calls `_generate_unique_public_id()` which retries up to 10 times to avoid collisions, then falls back to a 15-char token.

**`ajax_slug`** *(property)* — Returns `"{id}-{slug}"` if the model has a slug, otherwise `"{id}-{token}"`. Used to build AJAX dispatch URLs.

**`get_ajax_url`** *(property)* — Returns the full AJAX dispatch URL for the object, using `cmnsd:dispatch_object_by_id_and_slug`.

**`disallow_access_fields`** *(property)* — Returns `['id', 'slug', 'date_created', 'date_modified']`. Override in subclasses to protect additional fields from AJAX writes.

**`get_optimized_queryset()`** *(classmethod)* — Returns `cls.objects.all()` by default. Override in subclasses to add `select_related`, `prefetch_related`, and annotations.

**`get_model_fields()`** *(classmethod)* — Returns a list of all field names from `_meta.get_fields()`.

**`get_searchable_fields()`** *(classmethod)* — Returns field names plus any methods decorated with `@searchable_function`.

**`filter_status(queryset, request=None)`** *(classmethod)* — Filters a queryset by status based on the user:
- Anonymous → published only (`status='p'`)
- Authenticated → published + own concepts
- Staff → published + concepts + revoked

### Usage

```python
from cmnsd.models.BaseModel import BaseModel

class MyModel(BaseModel):
  name = models.CharField(max_length=255)

  class Meta:
    # Do NOT set abstract = True unless this is itself a base model
    pass
```

---

## VisibilityModel

**File:** `cmnsd/models/VisibilityModel.py`

Abstract mixin for models that need audience-based visibility control. Always combine with `BaseModel`.

### Field

| Field | Type | Notes |
|---|---|---|
| `visibility` | `CharField(1)` | `'p'` public, `'c'` community, `'f'` family, `'q'` private. Default from `DEFAULT_MODEL_VISIBILITY` setting (falls back to `'c'`). |

### Methods

**`filter_visibility(queryset, request=None)`** *(classmethod)* — Filters a queryset to only rows the current user may see:

| User state | Visible |
|---|---|
| Anonymous | `visibility='p'` only |
| Authenticated | public + community + family (own or in user's family) + private (own) |
| Staff | same as authenticated — staff does not bypass visibility |

```python
comments = VisibilityModel.filter_visibility(Comment.objects.all(), request=request)
```

**`is_visible_to(user=None)`** *(instance method)* — Same logic as `filter_visibility` but evaluated in Python on a single already-loaded instance. Use in detail views to avoid an extra query.

```python
# Filter a Python list (e.g. already-loaded nearby locations)
nearby = [loc for loc in candidates if loc.is_visible_to(request.user)]
```

**Convenience properties:** `is_private`, `is_family`, `is_community`, `is_public` — each returns a bool.

### Usage

```python
from cmnsd.models.BaseModel import BaseModel
from cmnsd.models.VisibilityModel import VisibilityModel

class Comment(BaseModel, VisibilityModel):
  text = models.TextField()
```

---

## BaseTag (Tag)

**File:** `cmnsd/models/Tag.py`

Abstract base for self-referencing tag hierarchies. Provides a two-level `parent → child` structure with auto-slug generation.

### Fields

| Field | Type | Notes |
|---|---|---|
| `slug` | `CharField(64)` | Unique. Auto-generated from `name` if blank. |
| `name` | `CharField(128)` | Display name. Auto-generated from `slug` if only slug is provided. |
| `parent` | `ForeignKey("self")` | Nullable. `on_delete=CASCADE` — deleting a parent deletes all children. |
| `description` | `TextField` | Optional. Explains why the tag exists. |

### Constraints

- `unique_name_per_parent` — a tag name must be unique within its parent (or among root tags).

### Methods

**`save()`** — Bidirectional auto-generation: fills `name` from `slug` or `slug` from `name` if either is blank.

**`display_name()`** — Returns `"Parent: Name"` if a parent exists, otherwise just `"Name"`. Used by `__str__`.

### Usage

```python
from cmnsd.models.Tag import Tag

class Tag(Tag):  # concrete subclass in your app
  class Meta:
    pass  # migrations live here
```

Project-level tags must be concrete (non-abstract) subclasses so they get their own database table and migrations.

---

## BaseCategory (Category)

**File:** `cmnsd/models/Category.py`

Abstract base for self-referencing category hierarchies. Similar to `Tag` but with a `"Parent: Child"` name-parsing shortcut in `save()`.

### Fields

| Field | Type | Notes |
|---|---|---|
| `slug` | `CharField(255)` | Unique. Auto-generated from `name`. |
| `name` | `CharField(255)` | Display name. |
| `parent` | `ForeignKey("self")` | Nullable. `on_delete=CASCADE`. |

### Methods

**`save()`** — If `name` contains a colon (e.g. `"Activity: Hiking"`), it splits on the first colon, looks up or creates the parent category by name, and stores only the child name. Slug is then auto-generated from the final `name`.

**`__str__()`** — Returns `"Parent: Name"` or just `"Name"`.

### Usage

```python
from cmnsd.models.Category import Category

class Category(Category):
  class Meta:
    pass
```

---

## BaseComment

**File:** `cmnsd/models/Comment.py`

Abstract base for comments that can be attached to **any model** using Django's `GenericForeignKey`. Inherits both `BaseModel` and `VisibilityModel`.

### Fields

| Field | Type | Notes |
|---|---|---|
| `content_type` | `ForeignKey(ContentType)` | Points to the model class the comment belongs to. |
| `object_id` | `PositiveBigIntegerField` | Primary key of the target object. |
| `content_object` | `GenericForeignKey` | Convenience accessor combining the two above. |
| `text` | `TextField` | Required. Markdown supported. Cannot be empty. |
| `title` | `CharField(255)` | Optional. Blank by default. |

Inherits `token`, `status`, `date_created`, `date_modified`, `user`, `visibility` from its parents.

### Methods

**`save()`** — Raises `ValueError` if `text` is blank or whitespace-only.

**`get_title()`** — Returns `title` if set, otherwise a 60-character truncated preview of `text`.

**`ajax_fields`** *(property)* — `["text", "title", "visibility"]` — the fields AJAX may update.

**`disallow_access_fields`** *(property)* — `["content_type", "object_id", "content_object"]` — AJAX cannot touch the generic FK internals.

**`get_searchable_fields()`** *(classmethod)* — `["text", "title", "user__username"]`.

### Attaching to a model

Use a `GenericRelation` on the target model to enable reverse access and automatic cascade deletion:

```python
from django.contrib.contenttypes.fields import GenericRelation
from locations.models.Comment import Comment

class Location(BaseModel, VisibilityModel):
  comments = GenericRelation(Comment)
```

Then access comments with `location.comments.all()`. When a `Location` is deleted, its comments are deleted automatically via the `GenericRelation`.

### Filtering comments

Do **not** filter in the template. Add a method to the model that applies both status and visibility filtering:

```python
@ajax_function
def filtered_comments(self):
  from cmnsd.models import VisibilityModel
  queryset = self.comments.filter(status='p').order_by('-date_created')
  if hasattr(self, 'request'):
    queryset = VisibilityModel.filter_visibility(queryset, request=self.request)
  else:
    queryset = queryset.filter(visibility='p')
  return queryset
```

---

## BaseMethods — `@ajax_function` and `@searchable_function`

**File:** `cmnsd/models/BaseMethods.py`

Two lightweight decorators that mark model methods for use by the cmnsd AJAX dispatch system.

### `@ajax_function`

Marks a method as callable via the AJAX dispatch URL (`/json/<model>/<id>-<slug>/<field>/`).

```python
from cmnsd.models.BaseMethods import ajax_function

class Location(BaseModel):

  @ajax_function
  def nearby(self, radius_km=None):
    ...

  @ajax_function
  def filtered_comments(self):
    ...
```

The dispatcher (`ajax_utils_meta_model.has_function`) verifies the decorator by checking `callable(func) and getattr(func, 'is_ajax_callable', False)` on the **model class** attribute.

### `@searchable_function`

Marks a method as a searchable field, included in `get_searchable_fields()` results.

---

## Critical caveat: `@property` and `@ajax_function` are incompatible

**Do not combine `@property` with `@ajax_function`.**

When Python resolves `getattr(MyModel, 'method_name')` on the *class* (not an instance), a `@property`-decorated attribute returns the `property` descriptor object — not the underlying function. `property` objects are not callable in Python 3, so `has_function()` always returns `False` and the dispatcher raises a field-not-found error before the method is ever reached.

```python
# BROKEN — has_function() returns False, AJAX dispatch fails
@property
@ajax_function
def filtered_comments(self):
  ...

# CORRECT — callable on the class, is_ajax_callable is found
@ajax_function
def filtered_comments(self):
  ...
```

Django templates automatically call zero-argument callables, so removing `@property` has no effect on template usage: `{{ location.filtered_comments }}` and `{% for c in location.filtered_comments %}` both work identically with a plain method.

The rule of thumb: **use `@property` for attributes that should never be AJAX-accessible; use `@ajax_function` (without `@property`) for anything the dispatcher needs to reach.**
