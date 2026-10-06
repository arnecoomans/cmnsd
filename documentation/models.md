# Models

cmnsd gives a project small abstract mixins, not one base model: a model inherits only the capabilities it needs, and the list of mixins *is* its capability declaration. Plus a few near-complete base models, and one concrete model, `Page`.

## The mixins

All in `models/mixins/`, imported from `cmnsd.models.mixins`.

| Mixin | Adds |
|---|---|
| `TimestampMixin` | `date_created`, `date_modified` |
| `TokenMixin` | `token`: unique, unguessable, generated on save - the identifier for URLs and the API |
| `SlugMixin` | `slug`, from `get_slug_source()` |
| `StatusMixin` | `status`: concept, published, revoked, deleted - and `filter_status()` |
| `OwnershipMixin` | `user`: the owner, required (see below) |
| `VisibilityMixin` | `visibility`: public, community, family, private - and `filter_visibility()`, `is_visible_to()` |
| `PartialDateMixin` | `year`, `month`, `day` (each optional) and `date_qualifier` (exact, ca., before, after); `partial_date_display()`, `is_exact_date()`, `as_date()` |
| `HierarchyMixin` | `parent`; `"Media: Book"` saves as Book under Media; `display_name()`, `ancestors()` |
| `TranslationAliasMixin` | `translation_alias`: the name in every language that has a translation, for search |
| `EditableRelationsMixin` | `link` / `unlink` actions for many-to-many relations edited on the page ([Edit mode](edit-mode.md)) |
| `SearchableMixin` | No fields; field discovery helpers |

Status and visibility together decide who sees a row: [Status, visibility and access](access.md).

## Composing a model

```python
from django.db import models
from cmnsd.api import api_model
from cmnsd.models.mixins import TimestampMixin, TokenMixin, StatusMixin, OwnershipMixin, VisibilityMixin


@api_model(search_fields=['title'])
class Storyline(TimestampMixin, TokenMixin, StatusMixin, OwnershipMixin, VisibilityMixin, models.Model):
  title = models.CharField(max_length=255)
  body = models.TextField(blank=True)
```

- **Only what it needs.** A model with a different lifecycle (open / answered) defines its own `status` field instead of `StatusMixin`.
- **`save()` calls `super()`.** `TokenMixin` and others hook into `save()`; an override that doesn't call `super().save(*args, **kwargs)` breaks the chain.
- **Save-time steps are explicit.** `HierarchyMixin` and `TranslationAliasMixin` expose a method (`_split_compounded_name()`, `_update_translation_alias()`) that the model's own `save()` calls, in the right order. `BaseTag.save()` is the example.
- **`Meta` isn't inherited.** A concrete model declares its own.

## Ownership needs the request

`OwnershipMixin.user` has no default: "whoever is signed in" needs the request. Fill it from the view or the admin:

- `cmnsd.views.mixins.OwnershipViewMixin` - for a `CreateView`: sets the owner on creation, never on update.
- `cmnsd.admin.mixins.OwnershipAdminMixin` - pre-fills the admin's add form, still editable ([The admin](admin.md)).

API create and edit-mode forms set it themselves.

## Base models

In `models/` (not `mixins/`): nearly complete models a project subclasses once, usually in a `core` app, under the same name without `Base`.

| Base | Contains | The project adds |
|---|---|---|
| `BaseTag` | token, owner, hierarchy, translation alias; `name`, `slug`, `description` | timestamps, status, visibility, as it wants |
| `BaseComment` | timestamps, token, status, owner; `content` and a generic `target` - any model | visibility, if comments need it; a `GenericRelation` on each commentable model |
| `BasePreferences` | `user` (one-to-one, `related_name='preferences'`), `language`, `ui_state` | the project's own preferences |

`Preferences` is required: `UserLanguageMiddleware` reads `user.preferences.language`, and remembered sections and sort orders live in `ui_state` (`ui/state.py`). The row is created on demand.

```python
# core/models.py
from cmnsd.models import BaseTag, BaseComment, BasePreferences
from cmnsd.models.mixins import TimestampMixin, StatusMixin, VisibilityMixin

class Tag(TimestampMixin, StatusMixin, VisibilityMixin, BaseTag): ...
class Comment(BaseComment): ...
class Preferences(BasePreferences): ...
```

## Page

A concrete model every project gets as is: a slug, a language, a title and a markdown body - for the cookie statement, a privacy page, an about page. Served at `pages/<slug>/` in the visitor's language, falling back to the site's (`views/pages/page_detail.py`). Edited in the admin.
