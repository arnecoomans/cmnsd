# The API

A JSON API for any registered model: lists, fields, actions and edit-mode forms, always filtered by what the viewer may see. cmnsd.js is its client; pages and the API render the same templates, so a page and a live update look identical.

## Nothing is exposed by default

```python
from cmnsd.api import api_model, api_field, api_action

@api_model(search_fields=['title'])
class Storyline(TokenMixin, StatusMixin, VisibilityMixin, models.Model):
  title = models.CharField(max_length=255)

  @api_field()
  def get_summary(self, request=None):        # readable: api/storyline/<token>/get_summary/
    ...

  @api_action()
  def add_chapter(self, request, data):       # callable: POST to the same URL
    require_can_edit(self, request)
    ...
    return {'chapter': chapter}
```

- **`@api_model(name=None, *, status=True, visibility=True, search_fields=())`** - registers the model under its lowercase name. Status and visibility filtering are applied when the model has them; `False` turns that off for a field that means something else.
- **`@api_field(*, readonly=True)`** - exposes a stored field or a method for reading. An undecorated field can't be read, and can't be filtered on.
- **`@api_action(*, requires_auth=True)`** - exposes a method that changes something. Called as `method(request=..., data=...)`; returns a dict.

Every registered model needs a `token` (or `slug`): objects are never looked up by sequential id. The registry is in `api/registry.py`, the system checks in `checks/ApiChecks.py`.

## Endpoints

Mounted at `api/` (see [Installation](installation.md)):

| URL | Method | Does |
|---|---|---|
| `<model>/?q=...&<field>=...` | GET | The visible objects, narrowed (`views/api/object_list.py`) |
| `<model>/<token>/` | GET | All exposed fields of one object |
| `<model>/<token>/<field>,<field>/` | GET | Some fields |
| `<model>/<token>/<action>/` | POST | Call an action |
| `<model>/<token>/form/<block>/` | GET, POST | An edit-mode block: its form, then save ([Edit mode](edit-mode.md)) |
| `<model>/<token>/children/<relation>/...` | GET, POST | Add, edit and remove child records |
| `<model>/new/` | GET, POST | Create an object from a small form, in a dialog |
| `<model>/suggest/<name>/?q=...` | GET | Recurring values of a free-text field, most used first |

Before anything else, every endpoint finds the object among those the viewer may see: hidden and missing both answer 404 (`views/api/lookup.py`).

## Filtering a list

Only what's declared narrows a list (`api/filtering.py`):

- `?q=jan bakker` - every word must match one of `search_fields` (`CMNSD_SEARCH_CHARACTER` sets the name).
- `?<field>=value` - an exact match, only on stored fields exposed with `@api_field`.
- A model may add its own search with a classmethod `api_search_q(term, request)` returning a `Q` - and must only search what the viewer may see.
- `format=picker` - compact rows for a picker, best match first.

Anything else is ignored and reported in `errors`. An open filter on any field would let a caller ask yes-or-no questions about rows they can't see.

## The response

One shape for every endpoint, success or error (`views/api/response.py`):

```json
{"ok": true, "model": "storyline", "token": "aB3dE5fG7h", "html": "...",
 "messages": [{"text": "Saved", "level": "success", "tags": "success"}]}
```

`ok` is false from status 400 up, with `error` - one readable sentence - and `errors` for code: `validation`, `stale`, `permission`, `unknown_fields`. `messages` holds the Django messages queued during the request. In `DEBUG` there may be a `debug` key.

## Templates

The API renders HTML from the project's templates, named by model:

| What | Template |
|---|---|
| A stored field / a method | `<model>/fields/<field>.html` / `<model>/functions/<method>.html` |
| A list / picker rows | `<model>/<model>_list.html` / `<model>/<model>_picker.html` |
| An action's result | `<model>/actions/<action>.html`, else `actions/<action>.html` |
| An edit block / its form | `<model>/blocks/<block>.html` / `<model>/forms/<block>.html` |

The object is in the context under its model name (`storyline`), with `request`. A field without a template returns its value, escaped. Fragments are minified.

## Hooks a model may define

| Hook | For |
|---|---|
| `api_display(request)` | The name as this viewer may see it - lists, pickers, messages |
| `api_search_q(term, request)` | Extra search conditions |
| `api_edit_forms = {block: form}` | Edit-mode blocks |
| `api_editable_children = {relation: {...}}` | Child records edited in place |
| `api_editable_relations = {relation: {...}}` | Many-to-many links (`EditableRelationsMixin`) |
| `api_create_form = form` | `new/` in a dialog |
| `api_suggest_fields = {name: lookup}` | Suggestions |
| `can_edit(user)` | Who may change this object ([Edit mode](edit-mode.md)) |
| queryset `for_list()` | Batch loading for list rows |

Forms may be given as a dotted path: a model can't import its own app's forms module.
