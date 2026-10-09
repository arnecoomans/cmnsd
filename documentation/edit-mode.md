# Edit mode

Changing things on the page itself instead of in the admin. A switch in the header turns it on; pages then show their edit controls to whoever may change each object. Switched off, a page is exactly what any visitor sees.

## The switch

`edit/mode.py`, posted to `cmnsd_ui:edit_mode` (`ui/edit/`, from [Installation](installation.md)) with `on=1|0` and `next=<this page>`:

- **Who gets it:** signed in, active, and holding at least one Django `change_*` permission (superusers hold all). `{{ can_edit_mode }}` says whether to show it.
- **How long:** the session. It ends at sign-out and is never stored in preferences.
- **What it grants:** nothing. `{{ edit_mode }}` only decides whether controls are rendered; each control also checks the object.

## Who may change an object

```django
{% load edit_mode %}
{% if edit_mode and storyline|can_edit:request %}...{% endif %}
```

`can_edit` uses the object's own `can_edit(user)` when the model defines one, otherwise the model's `change_<model>` permission. The API checks the same thing on every save; an `@api_action` that changes something calls `require_can_edit(obj, request)` (403 otherwise). The switch is UI - the permission protects the data.

One template per page for both modes: edit controls are small includes under that `{% if %}`, so a page outside edit mode carries no edit HTML.

## Editable blocks

A group of fields edited together - a name, a date and place. The model lists its blocks and their forms:

```python
api_edit_forms = {'title': 'stories.forms.StorylineTitleForm', 'body': 'stories.forms.StorylineBodyForm'}
```

The page includes each block:

```django
{% include 'cmnsd/edit/block.html' with model='storyline' obj=storyline block='title' %}
```

That renders `storyline/blocks/title.html` - the block as the page shows it - plus, in edit mode, a pencil. The pencil opens the form in place (`storyline/forms/title.html`, else the generic `cmnsd/edit/form.html`); Save posts it, and the saved block replaces the form. Escape cancels, Ctrl/Cmd+Enter saves.

- **Changed meanwhile:** the form carries the object's `date_modified`; a save over a newer version is refused (409) with "changed by someone else - reload".
- **Choice blocks:** for a field with fixed choices (status, visibility) the form class sets `choice = True` and the block template calls `{% edit_choices obj 'visibility' %}`: buttons that save on click, no pencil. `confirm = {value: question}` asks yes or no first; `prompt = {value: question}` asks for an answer instead - a reason - posted along as the form's `prompt_field` (cancelled or empty: nothing is saved).
- **In a dialog:** `dialog="<title>"` on the include opens the form over the page, for a form that needs room.
- **Opening on load:** `?open=title,body` in the address opens those blocks' forms.
- **A related record:** a form class with `instance_for(obj)` edits a related row (an item's photo details), while history and the stale check stay on the object.

## Relations and child records

- **Many-to-many links** (tags, people on a photo): `EditableRelationsMixin` adds `link` and `unlink` actions for the relations in `api_editable_relations`. The page uses `cmnsd/edit/link_picker.html` - search, choose, optionally create - and `cmnsd/edit/unlink.html`.
- **Child records** (an item's transcripts): `api_editable_children` on the model; the page includes `cmnsd/edit/children.html`. Each child is a block with a pencil and a remove button, plus "+ add".
- **A new object in a dialog:** `api_create_form` on the model; a picker's "+ new" opens it (`cmnsd/edit/create_form.html`).

## The change log

Every save through edit mode is written to Django's admin log, so it shows in the object's admin **History** next to changes made in the admin (`edit/log.py`). From your own action:

```python
from cmnsd.edit.log import log_change
log_change(request, storyline, "Added chapter 3")
```

## More

The client side - `edit.js`, `dialog.js`, `picker.js`: [cmnsd.js](javascript/readme.md). The endpoints: [The API](api.md).
