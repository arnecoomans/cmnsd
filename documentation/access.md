# Status, visibility and access

Who may see a row is decided in one place: the model's `StatusMixin` and `VisibilityMixin`. Every list, detail page, file download and API call goes through them, so no two parts of a site can disagree about it.

## Status: where a row is in its life

| Status | Seen by |
|---|---|
| `p` published | everyone (still subject to visibility) |
| `c` concept | its owner and staff - a draft |
| `r` revoked | staff - pulled back, kept for reference |
| `x` deleted | no one - kept in the database, gone from the site |

New rows get `CMNSD_DEFAULT_MODEL_STATUS` (published unless set). `needs_attention` is true for concept and revoked: the few who see such a row should see it marked.

## Visibility: who it's meant for

| Visibility | Seen by |
|---|---|
| `p` public | everyone, signed in or not |
| `c` community | every signed-in user - the default |
| `f` family | the owner, and the people the owner counts as family |
| `q` private | the owner only |

"Family" needs `CMNSD_VISIBILITY_FAMILY_LOOKUP_STORAGE`: the lookup path from the row to those people, such as `'user__preferences__family'` (the owner's `Preferences.family`). Without it, family means the owner alone.

Staff see no more than anyone else by visibility: a private row stays private.

## filter_accessible: the one call

```python
from cmnsd.models.access import filter_accessible

storylines = filter_accessible(Storyline.objects.all(), request)
```

Status first, then visibility, each only when the model has the mixin. Use it wherever a viewer gets objects: views, querysets (`objects.visible_to(request)`), template tags, files. Combine with other filters freely; it returns a queryset.

In class-based views, `VisibilityViewMixin.get_accessible_queryset(queryset)` does the same (`views/mixins/VisibilityViewMixin.py`).

## One loaded object

For objects that are already loaded - a related row, an avatar - check in Python instead of a query per object:

```python
obj.is_status_visible_to(request.user) and obj.is_visible_to(request.user)
```

These mirror `filter_status()` and `filter_visibility()` exactly; a change to one is a change to the other (`models/mixins/StatusMixin.py`, `VisibilityMixin.py`).

## In the API

The API applies the same two filters to every model it serves, before anything else (`api/filtering.py`). A model can opt out of the default logic in its registration - `@api_model(status=False)` - when it has a status field that means something else. See [The API](api.md).

## Things that aren't rows

A name shown on a page can belong to a row the viewer may not see: a hidden person on a visible event. `{{ obj|viewer_name:request }}` shows an object's name as this viewer may see it - its `api_display(request)` if the model defines one. Use it wherever a project shows names of arbitrary objects ([Templates and tags](templates.md)).

## Testing access

For anything that shows objects, test a viewer who may **not** see them: a signed-out visitor, another account, a concept or private row. Most bugs worth catching are a hidden name or count that shows up anyway.
