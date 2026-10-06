# The admin

`ModelAdmin` mixins that pair with the model mixins: list filters, read-only fields and bulk actions, so a model's admin gets what its mixins need without repeating it per project. In `admin/mixins/`, imported from `cmnsd.admin.mixins`.

## The mixins

| Admin mixin | For | Adds |
|---|---|---|
| `TimestampAdminMixin` | `TimestampMixin` | `date_created`, `date_modified` read-only |
| `OwnershipAdminMixin` | `OwnershipMixin` | The add form starts with the current user as owner - still editable, to add on someone's behalf |
| `StatusAdminMixin` | `StatusMixin` | Filter on status; actions "Mark as Concept / Published / Revoked / Deleted" |
| `VisibilityAdminMixin` | `VisibilityMixin` | Filter on visibility; an action per visibility |
| `HierarchyAdminMixin` | `HierarchyMixin` | The full name ("Media: Book") in the list |
| `TranslationAliasAdminMixin` | `TranslationAliasMixin` | The alias read-only; action "Refetch translation aliases" |

`TokenMixin` needs none: the token isn't editable, so the admin leaves it out.

## Using them

```python
from django.contrib import admin
from cmnsd.admin.mixins import (
  TimestampAdminMixin, StatusAdminMixin, VisibilityAdminMixin, OwnershipAdminMixin,
)
from .models import Storyline


@admin.register(Storyline)
class StorylineAdmin(TimestampAdminMixin, StatusAdminMixin, VisibilityAdminMixin, OwnershipAdminMixin, admin.ModelAdmin):
  list_display = ('title',)
  actions = ['mark_status_p', 'mark_status_r', 'mark_visibility_c', 'mark_visibility_q']
```

**Bulk actions are opt-in.** A mixin makes its actions available, but only the ones named in `actions` appear in the dropdown: an action changes data for everyone with access to the list, so each admin chooses. Names: `mark_status_<c|p|r|x>`, `mark_visibility_<p|c|f|q>`, `refetch_translation_aliases`.

The status and visibility actions update in one query (`queryset.update`). "Refetch translation aliases" saves each row instead, because the alias is computed on save - use it after adding translations to the `.po` catalog and running `compilemessages`.

## Writing another mixin

Each mixin overrides Django's `get_*()` hook - `get_list_filter`, `get_readonly_fields`, `get_list_display`, `get_actions` - calls `super()` first and adds to the result:

```python
def get_list_filter(self, request):
  return (*super().get_list_filter(request), 'status')
```

Never a class attribute (`list_filter = ('status',)`): with two mixins setting the same attribute, the last one silently wins. The helper for one action per choice is `attach_set_field_actions()` in `admin/actions.py`.

`raw_id_fields` has no `get_` hook, so no mixin sets it; set it on the concrete admin when a list grows long.

## Changes made on the site

Changes made in edit mode are written to the same admin log, so an object's **History** in the admin shows both ([Edit mode](edit-mode.md)).
