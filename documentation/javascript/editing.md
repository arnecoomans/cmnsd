# Editing

The client side of [Edit mode](../edit-mode.md): blocks that turn into forms, pickers to choose an object, dialogs, suggestions and forms that save themselves. The server side - which blocks exist, who may save - is on that page.

## Editable blocks (edit.js)

`cmnsd/edit/block.html` renders a block with a pencil. The pencil gets the block's form (`api/<model>/<token>/form/<block>/`) and puts it in place of the block:

- **Save** posts it. Saved: the updated block replaces the form, "Saved." shows, and the address follows the object's new URL after a rename. A validation error returns the form with its errors; a 409 (changed by someone else) or 403 shows in the form.
- **Cancel** or **Escape** puts the block back, without a request. **Ctrl/Cmd+Enter** saves.
- **`?open=title,body`** in the address opens those blocks on load, focus in the first.
- **Unsaved changes:** leaving the page with an open, changed form gets the browser's warning. A form marked `data-cmnsd-unsaved="<question>"` (such as the edit-mode switch) asks that question first.
- **Choice blocks** (`cmnsd/edit/choices.html`): each button saves its own value; with `data-cmnsd-confirm` it asks first. The response may say `redirect` (the object is gone for this viewer) or `reload`.

After every save the response carries the object's new version, and edit.js puts it in the page's other open forms for the same object: saving two blocks in a row works, only someone else's change in between is refused.

## Pickers (picker.js)

Search for an object and choose it. As an **action form** - choosing submits it:

```html
<form data-cmnsd-picker="tag" data-picker-param="q" data-picker-exclude="{{ storyline.tags.all|tokens }}"
      data-cmnsd-action="link" data-model="storyline" data-object-token="{{ storyline.token }}" data-cmnsd-insert="append" ...>
  <input type="search" data-picker-input>
  <input type="hidden" name="token" data-picker-value>
  <div data-picker-results></div>
</form>
```

`cmnsd/edit/link_picker.html` writes this for a relation. Typing (two characters or more) asks `api/<model>/?q=...&format=picker`, which renders `<model>/<model>_picker.html` - rows with a `[data-picker-choose="<token>"]` button, best match first. Enter takes the first, arrows move, Escape clears.

- `data-picker-exclude` - tokens not to offer; a chosen one is added, so several can be added in a row.
- `data-picker-create="<label>"` - without an exact match, offer to create one by name (a tag).
- `data-picker-new-dialog="<api/<model>/new/>"` - without an exact match, "+ new" opens the model's create form in a dialog; the new object is then chosen like a result.
- `data-picker-new-url` - for a model created on a page of its own: a link there in a new tab.
- `data-picker-as="object"` - the chosen object becomes the action's object instead.

As a **form field** - one object, such as a parent - use the widget on a `ModelChoiceField`:

```python
parent = forms.ModelChoiceField(Place.objects.all(), to_field_name='token', required=False,
                                widget=PickerInput('place', clear_label=_("remove")))
```

## Dialogs (dialog.js)

A form over the page, in a native `<dialog>`: `formDialog(url, {title, accept})` for any form, `createDialog(url, {title})` for a new object - it resolves with `{token, name, url}`, or `null` when closed. A validation error puts the form back with its errors. Escape, the close button, `[data-cmnsd-dialog-close]` or a click beside it close without saving.

A button `[data-cmnsd-create="<api/<model>/new/>"]` with `data-cmnsd-create-title` opens a create form; `data-cmnsd-create-then="open"` (default) goes to the new object, `"reload"` reloads the page.

## Suggestions (suggest.js)

For free text whose values recur - a publisher, a last name. The model declares `api_suggest_fields = {'publisher': 'details__publisher'}`; the form uses `SuggestInput(url=...)`. While typing, a `<datalist>` fills with up to ten existing values, most used first, from objects the viewer may see. Choosing one only fills in the text.

## Autosave (autosave.js)

A form marked `data-cmnsd-autosave` that posts to a block or child endpoint saves a moment after typing stops, when a field loses focus, and on Ctrl/Cmd+S - never when nothing changed. Made for long text, such as a transcript.

- `[data-autosave-status]` shows saving / saved / unsaved / error, in the words of its `data-text-*` attributes.
- A create answers with the new child; the form then keeps saving that one.
- A 409 stops autosaving until a reload. After each save the form fires `cmnsd:autosaved`.
- `[data-autosave-close="<form id>"]` - a close link that's disabled until everything is saved.
