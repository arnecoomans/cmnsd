# Model mixins

CMNSD provides composable abstract mixins instead of one monolithic base
model. A concrete model inherits only the mixins it actually needs — there's
no "inherit everything, ignore what doesn't apply."

Two different things live under `cmnsd/models/`, and they're not the same
kind of reusable piece:

- **`cmnsd/models/mixins/`** — capability mixins. Each adds one field/
  behavior to otherwise-unrelated models (a timestamp, a token, a parent
  hierarchy). None of them are "a thing" on their own.
- **`cmnsd/models/*.py`** (flat, not in `mixins/`) — near-complete entity
  blueprints (`BaseTag`, `BaseComment`, `BasePreferences`). Each *is* a
  specific thing, just without the capability mixins baked in, so every
  project using `cmnsd` can compose its own set and get one concrete
  subclass. See "Near-complete blueprint models" below.

## Available capability mixins

All live under `cmnsd/models/mixins/`.

| Mixin | Adds | Notes |
|---|---|---|
| `TimestampMixin` | `date_created`, `date_modified` | Fully automatic (`auto_now_add` / `auto_now`) |
| `TokenMixin` | `token` — unique, URL-safe public ID | Auto-generated in `save()` if not already set |
| `StatusMixin` | `status` (concept / published / revoked / deleted) + `filter_status(queryset, request)` | Default from `CMNSD_DEFAULT_MODEL_STATUS` |
| `OwnershipMixin` | `user` — required FK to the owner, `on_delete=PROTECT` | Needs a view/admin mixin to populate it — see below |
| `VisibilityMixin` | `visibility` (public / community / family / private) + `filter_visibility()`, `is_visible_to()`, `is_public`/`is_community`/`is_family`/`is_private` | Default from `DEFAULT_MODEL_VISIBILITY`; family tier needs `CMNSD_VISIBILITY_FAMILY_LOOKUP_STORAGE` |
| `SearchableMixin` | No fields. `__str__`, `get_optimized_queryset()`, `get_model_fields()`, `get_searchable_fields()` | Safe to add to any model |
| `PartialDateMixin` | `year`, `month`, `day` — each independently nullable — + `as_date()` | For dates that are often only partially known (e.g. a birth year with no exact day) |
| `HierarchyMixin` | `parent` (self-FK, `PROTECT`) + compound-name auto-split + `display_name()` + `ancestors()` | See "Compound-name hierarchies" below |
| `TranslationAliasMixin` | `translation_alias` (auto-populated) | See "Translation aliases" below |

## Composing a model

```python
from django.db import models
from cmnsd.models.mixins import (
  TimestampMixin, TokenMixin, StatusMixin, OwnershipMixin,
  VisibilityMixin, SearchableMixin,
)


class Storyline(TimestampMixin, TokenMixin, StatusMixin, OwnershipMixin,
                 VisibilityMixin, SearchableMixin, models.Model):
  title = models.CharField(max_length=255)
  body = models.TextField()
```

Rules for composing:

- Only inherit a mixin if the model needs that capability. A model with no
  draft/published lifecycle simply skips `StatusMixin`.
- A model that needs status-*like* behavior but a different set of states
  (e.g. `ResearchQuestion` using open/answered) does **not** inherit
  `StatusMixin` — it defines its own `status` field directly. Which mixins a
  model inherits *is* its capability declaration; there's no separate flag
  to say "ignore this part of the mixin."
- `TokenMixin` overrides `save()`. If a concrete model (or another mixin)
  also overrides `save()`, it must call `super().save(*args, **kwargs)` so
  the chain resolves correctly through the MRO.
- `Meta.abstract = True` does not propagate. A concrete model that wants
  `Meta` options from a mixin must declare its own `Meta`, not assume one is
  inherited.
- A field-level mixin (`HierarchyMixin`, `TranslationAliasMixin`) that needs
  something done at save time does **not** override `save()` itself if the
  timing matters relative to other save()-time logic — it exposes a plain
  method (`_split_compounded_name()`, `_update_translation_alias()`) and the
  concrete model's own `save()` calls it explicitly, in the right order. See
  `BaseTag.save()` for both being used together.

## Settings the mixins read

| Setting | Used by | Default if unset |
|---|---|---|
| `CMNSD_DEFAULT_MODEL_STATUS` | `StatusMixin` | `'p'` (Published) |
| `DEFAULT_MODEL_VISIBILITY` | `VisibilityMixin` | `'c'` (Community) |
| `CMNSD_VISIBILITY_FAMILY_LOOKUP_STORAGE` | `VisibilityMixin` | none — without it, `visibility='f'` only ever matches the record's own owner |
| `CMNSD_PARENT_COMPOUNDER` | `HierarchyMixin` | `': '` |

`CMNSD_VISIBILITY_FAMILY_LOOKUP_STORAGE` is a Django `__`-lookup path from
the model to the manager whose members should also see that model's
`family`-visibility records — e.g. `'user__preferences__family'`.

## Compound-name hierarchies

`HierarchyMixin` gives any model with a `name` `CharField` a self-referential
`parent` (`on_delete=PROTECT` — deleting a node with children is blocked
until they're re-parented or removed, not silently cascaded away).

The useful part is `_split_compounded_name()`: saving `name="Media: Book"`
with no `parent` already set `get_or_create`s a root `"Media"` tag/place/etc.
and leaves `self` as just `"Book"` under it — repeated for further levels
(`"Media: Book: Fiction"` resolves three deep, reusing existing ancestors
rather than duplicating them). An **explicitly-set `parent` always wins**
over the string heuristic — the split only runs when `parent` is unset — and
`clean()` rejects a `name` that still contains the compounder afterward
(covers the case where `parent` was set explicitly *and* `name` still has
the separator in it — ambiguous, not allowed).

```python
Tag.objects.create(user=owner, name='Media: Book')
# -> name='Book', parent=<Tag: Media>
```

`display_name()` renders the full chain as a string (`"Media: Book"`);
`ancestors()` returns it as a list, root-first
(`[<Media>, <Book>]`) — for showing/tagging at any level, not just the leaf.

This is a pure string heuristic: any name that happens to contain the exact
compounder substring gets treated as hierarchical, even if that wasn't the
intent (a tag genuinely named `"Time: A History"` would get split). Known
trade-off, not a bug.

Because `_split_compounded_name()` isn't wired to `save()` automatically
(see the composing rule above), the concrete model must call it itself —
`BaseTag.save()` is the reference implementation.

## Translation aliases

`TranslationAliasMixin` adds `translation_alias`, auto-populated from every
configured language's translation of `self.name` that differs from the
stored value — makes `name` searchable across languages without touching
the search layer (`FilterMixin`-style filtering auto-discovers plain
`TextField`s).

**This does not generate translations.** `gettext()` only finds a match if
the *exact stored string* already has a `msgid`/`msgstr` entry in the
compiled `.po` catalog, and `makemessages` only extracts strings from source
code, never from database content. Translating a dynamic value like a tag
name requires hand-adding that entry to `locale/<lang>/LC_MESSAGES/django.po`
and running `compilemessages` — this mixin surfaces an existing translation,
it doesn't create one.

Like `HierarchyMixin`, `_update_translation_alias()` isn't wired to `save()`
automatically — the concrete model calls it explicitly, after `name` is
fully resolved (so the alias reflects the actual leaf name, not a pre-split
compound one — order matters when a model uses both mixins together).

Because the underlying `.po` catalog can gain new entries after a row was
last saved, there's a bulk "Refetch translation aliases" admin action to
force a re-save and pick up anything added since — see `admin.md`.

## OwnershipMixin needs a paired view/admin mixin

`OwnershipMixin.user` is required and has no `default=` — it can't have one,
since the only sensible default ("whoever is currently logged in") needs
the request, and a field default only gets a static value or a no-arg
callable. Two mixins fill that gap from the request layer instead:

- **`cmnsd.views.mixins.OwnershipViewMixin`** — for `CreateView`-style
  views. Sets `form.instance.user = self.request.user` in `form_valid()`,
  only when `form.instance.pk is None` — an existing owner is never
  overwritten on update.
- **`cmnsd.admin.mixins.OwnershipAdminMixin`** — for `ModelAdmin`. Pre-fills
  the `user` field with the current user via `get_changeform_initial_data()`
  on the add form, but leaves it editable — staff can still enter content on
  behalf of another family member.

```python
# views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView
from cmnsd.views.mixins import OwnershipViewMixin


class StorylineCreateView(LoginRequiredMixin, OwnershipViewMixin, CreateView):
  model = Storyline
  fields = ['title', 'body']
```

This is specifically about populating a *request-dependent default* — it's
not the full picture of what admin mixins exist. `StatusMixin`,
`VisibilityMixin`, `TimestampMixin`, `HierarchyMixin` and
`TranslationAliasMixin` all have their own admin mixins too (list filters,
readonly fields, bulk actions), just for different reasons than "populate a
default." See **`cmnsd/docs/admin.md`** for the full catalog.

`TokenMixin` and `SearchableMixin` don't need any admin mixin at all —
`token` is already `editable=False` (Django's admin excludes it from the
form automatically), and `SearchableMixin` has no fields.

## Near-complete blueprint models

`cmnsd/models/` (flat, **not** `mixins/`) holds abstract bases that are
almost a complete, usable model on their own — `BaseTag`, `BaseComment`,
`BasePreferences` — as opposed to a bolt-on capability. Each project using
`cmnsd` composes its own concrete subclass, typically in a `core` app:

```python
# core/models.py
from cmnsd.models import BaseTag, BaseComment, BasePreferences
from cmnsd.models.mixins import (
  TimestampMixin, StatusMixin, VisibilityMixin, SearchableMixin,
)


class Tag(TimestampMixin, StatusMixin, VisibilityMixin, SearchableMixin, BaseTag):
  pass

class Comment(BaseComment):
  pass

class Preferences(BasePreferences):
  pass
```

They're all named `Base*` (not `*Base`, and not sharing the bare concrete
name like `Tag`) deliberately: the concrete subclass in each project's
`core` app is expected to reuse the same name (`core.Tag`, `core.Comment`),
and `class Tag(Tag)` would be a real, confusing name collision between the
abstract base and its own concrete subclass.

| Base | Composes | Concrete needs to add | Notes |
|---|---|---|---|
| `BaseTag` | `TokenMixin`, `OwnershipMixin`, `HierarchyMixin`, `TranslationAliasMixin` | Whichever of `Timestamp`/`Status`/`Visibility`/`Searchable` the project wants | `slug` (auto-generated, unique per parent), `name`, `description`. `save()` orchestrates split → slug → translation-alias → `full_clean()`, in that order. |
| `BaseComment` | `TimestampMixin`, `TokenMixin`, `StatusMixin`, `OwnershipMixin` | `Visibility`, if the project wants per-comment scoping | `name` (optional), `content`, and `target`/`target_content_type`/`target_id` — a `GenericForeignKey`, so a comment can attach to any model without a migration on `Comment` itself. Each commentable model needs its own `comments = GenericRelation(Comment, content_type_field='target_content_type', object_id_field='target_id')` to get the reverse accessor — it's not automatic just from the `GenericForeignKey` existing. |
| `BasePreferences` | `TimestampMixin` only | Everything else — favorites, display settings, etc. are project-specific and don't belong in the shared base | `user` (`OneToOneField`, `related_name='preferences'`) + `language`. Named `Preferences`, not `Profile` — "profile" more naturally describes account/identity info; this is settings. `related_name='preferences'` is load-bearing: `cmnsd`'s own `UserLanguageMiddleware` reads `request.user.preferences.language` directly. |

Why `BaseTag`'s capability mixins are split the way they are: `Token` and
`Ownership` are intrinsic to what a tag *is* in any project (every tag
needs an identifying URL and a creator), so they're baked into the shared
base. `Timestamp`/`Status`/`Visibility`/`Searchable` are left for the
concrete subclass — a project might reasonably not want tags to have a
draft/published lifecycle, for instance. `BaseComment` follows the same
logic in the other direction: `Ownership` and `Status` are intrinsic to what
a comment *is* (who wrote it, its moderation state) so they're in the base;
`Visibility` isn't (some projects won't want per-comment scoping), so it's
left out.

## Registering with the dynamic API

Once a model composes the mixins it needs, register it with the CMNSD
dynamic API registry (`cmnsd/api/registry.py`) so it's discoverable without
per-model API code:

```python
from cmnsd.api import api_model


@api_model()
class Storyline(...):
  ...
```

`@api_model()` auto-detects the `status`/`visibility` capabilities by duck
typing (`filter_status`; `is_visible_to` + `filter_visibility`) and applies
CMNSD's default interpretation of them. Every `@api_model`-registered model
must have a `token` or `slug` field — `manage.py check` fails with
`cmnsd.api.E001` otherwise, since the API's `SecureLookupMixin` requires one
of these for every object lookup (never a bare pk, to prevent
ID-enumeration).
