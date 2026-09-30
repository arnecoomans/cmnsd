# Admin mixins

`cmnsd/admin/mixins/` provides `ModelAdmin` mixins that pair with the model
mixins in `cmnsd/models/mixins/` — `list_filter`/`readonly_fields`/
`list_display` additions and bulk actions, one mixin per model mixin that
needs one.

## The composition rule

Every mixin here overrides one of Django's `get_*()` hook methods
(`get_list_filter`, `get_readonly_fields`, `get_list_display`, `get_actions`)
and calls `super()` **first**, then appends to whatever came back:

```python
def get_list_filter(self, request):
  return (*super().get_list_filter(request), 'status')
```

Never a plain class attribute (`list_filter = ('status',)`). The reason:
model field mixins compose cleanly because Django's model metaclass collects
fields from every abstract base. Plain `ModelAdmin` attributes don't get
that treatment — if two mixins in a `TagAdmin`'s MRO both set
`list_filter = (...)` directly, whichever comes **last** in the MRO silently
wins and the other's contribution is just gone, no error. The `get_*()`
hooks are Django's own escape hatch for this, and every mixin below uses it.

One exception: `raw_id_fields` has no `get_raw_id_fields()` hook in Django's
`ModelAdmin` API — there's no safe way to compose it across mixins the same
way, so `HierarchyAdminMixin` deliberately doesn't set it. If a tag/place
list grows large enough to need it, set it directly on the concrete
`ModelAdmin`.

## Available admin mixins

All live under `cmnsd/admin/mixins/`.

| Admin mixin | Pairs with | Adds |
|---|---|---|
| `TimestampAdminMixin` | `TimestampMixin` | `date_created`/`date_modified` → `readonly_fields` |
| `OwnershipAdminMixin` | `OwnershipMixin` | Pre-fills `user` on the add form (see `models.md`) |
| `StatusAdminMixin` | `StatusMixin` | `status` → `list_filter`, + one bulk action per `Status` value |
| `VisibilityAdminMixin` | `VisibilityMixin` | `visibility` → `list_filter`, + one bulk action per `Visibility` value |
| `HierarchyAdminMixin` | `HierarchyMixin` | `display_name` → `list_display` (added, doesn't replace `name`) |
| `TranslationAliasAdminMixin` | `TranslationAliasMixin` | `translation_alias` → `readonly_fields`, + a `refetch_translation_aliases` bulk action |

`TokenMixin` and `SearchableMixin` have no admin mixin — `token` is already
`editable=False` (Django's admin excludes it from the form on its own), and
`SearchableMixin` has no fields to surface.

## Bulk actions are opt-in, not auto-registered

`readonly_fields`/`list_filter`/`list_display` additions apply automatically
just by composing the mixin — they're passive display conveniences, low
stakes either way. Bulk **actions** are different: they actively mutate data
for whoever has staff access to that changelist, so composing a mixin makes
the action *available* (attached to the class, correctly labelled, ready to
use) but never adds it to the admin's action dropdown on its own. The
concrete `ModelAdmin` opts in explicitly:

```python
# core/admin.py
from cmnsd.admin.mixins import StatusAdminMixin, TranslationAliasAdminMixin

class TagAdmin(StatusAdminMixin, TranslationAliasAdminMixin, admin.ModelAdmin):
  actions = ['mark_status_p', 'mark_status_r', 'refetch_translation_aliases']
```

Leaving `actions` unset means none of a mixin's actions show up, even though
the mixin is composed — that's deliberate, not a bug to work around.

### Status / Visibility bulk actions

`StatusAdminMixin`/`VisibilityAdminMixin` each attach one action per value in
their `TextChoices` — `mark_status_c`/`mark_status_p`/`mark_status_r`/
`mark_status_x` ("Mark as Concept"/"Published"/"Revoked"/"Deleted"), and the
equivalent `mark_visibility_p`/`_c`/`_f`/`_q`. Deliberately **not** a single
"change status..." action with an intermediate value-picker page (Django
supports that pattern too — an action can return an `HttpResponse` instead
of `None` to render a confirmation/selection page, same mechanism the
built-in "Delete selected" action uses) — with only 4 possible values each,
one action per value avoids the extra machinery (a template, a `Form` class,
two-step POST handling) for a small UX cost.

Both mixins get this via a shared helper rather than duplicating the
generation logic:

```python
# cmnsd/admin/actions.py
def attach_set_field_actions(cls, field_name, choices):
  ...

# cmnsd/admin/mixins/StatusAdminMixin.py
attach_set_field_actions(StatusAdminMixin, 'status', StatusMixin.Status.choices)
```

These use `queryset.update(**{field_name: value})` — a single `UPDATE`
statement, not a loop calling `.save()` per object — because `status`/
`visibility` are plain fields with no save()-time computation tied to their
value. Compare `refetch_translation_aliases` below, which specifically needs
`save()` to re-run.

### `refetch_translation_aliases`

`TranslationAliasMixin`'s `translation_alias` is computed from whatever's in
the `.po` catalog *at save time*. If a translation gets added to
`locale/<lang>/LC_MESSAGES/django.po` and `compilemessages` is run after a
row was already saved, that row's alias is stale until it's saved again.
This action re-saves each selected object (`obj.save()`, not
`queryset.update()` — the whole point is to re-run the model's own save()
logic) and reports how many were refreshed via `message_user()`.

## Full example

`core.Tag` composes every capability mixin `BaseTag` doesn't already bake
in, so its admin pulls in the whole catalog:

```python
# core/admin.py
from django.contrib import admin
from cmnsd.admin.mixins import (
  TimestampAdminMixin, StatusAdminMixin, VisibilityAdminMixin, OwnershipAdminMixin,
  HierarchyAdminMixin, TranslationAliasAdminMixin,
)
from .models import Tag


@admin.register(Tag)
class TagAdmin(
  TimestampAdminMixin, StatusAdminMixin, VisibilityAdminMixin, OwnershipAdminMixin,
  HierarchyAdminMixin, TranslationAliasAdminMixin,
  admin.ModelAdmin,
):
  list_display = ('name',)
  actions = [
    'mark_status_c', 'mark_status_p', 'mark_status_r', 'mark_status_x',
    'mark_visibility_p', 'mark_visibility_c', 'mark_visibility_f', 'mark_visibility_q',
    'refetch_translation_aliases',
  ]
```

Resulting `list_display`: `('name', 'display_name')` — the concrete class's
own `'name'` plus `HierarchyAdminMixin`'s addition, not one replacing the
other.
