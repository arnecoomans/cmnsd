# Actions and messages

Buttons and forms that change something through an `@api_action`, the message area that confirms it, and a few small helpers for forms and menus.

## Actions (actions.js)

A form or button marked `data-cmnsd-action` posts to `api/<model>/<token>/<action>/` and puts the returned `html` in place:

```django
<form data-cmnsd-action="add_comment" data-model="storyline" data-object-token="{{ storyline.token }}"
      data-cmnsd-target="#comments" data-cmnsd-insert="append">
  <textarea name="content"></textarea>
  <p data-cmnsd-error hidden></p>
  <button type="submit">Post</button>
</form>

<button type="button" data-cmnsd-action="delete_comment" data-model="comment" data-object-token="{{ comment.token }}"
        data-cmnsd-target="closest:.comment" data-cmnsd-insert="remove" data-cmnsd-confirm="Delete this comment?">Delete</button>
```

| Attribute | Value |
|---|---|
| `data-cmnsd-action`, `data-model`, `data-object-token` | Which action on which object |
| `data-cmnsd-target` | A CSS selector, or `closest:<selector>` - an ancestor of the form or button |
| `data-cmnsd-insert` | `append`, `prepend`, `replace`, `remove`, or `reload` - for a change that shows in more than one place |
| `data-cmnsd-confirm` | A question asked first |

- A form sends its fields as JSON; a button sends nothing, or `{name: value}` when it has both.
- After `append` the form is reset. An error goes into the form's `[data-cmnsd-error]`, else the message area.
- Delegated on the document: buttons in HTML added later - a new comment's own delete button - work without binding.
- The server side - the method, its permission check and the template for `html` - is in [The API](../api.md).

**Counters:** an element with `data-cmnsd-count="<list>"` and `data-cmnsd-count-items="<item>"` shows the number of items in that list after every action - a section's comment count. When the list isn't on the page (a section never opened), the server's number stays.

## Messages (messages.js)

`cmnsd/messages.html`, included once by the base template, is the message area. It shows the Django messages of the page load and, through `messages.js`, the `messages` of every API response - so `messages.success(request, "Comment added")` in an action appears without a reload.

- Success, info and debug fade after a few seconds; warnings and errors stay until closed.
- With `data-cmnsd-insert="reload"`, messages are kept across the reload and shown after it.
- From a script: `cmnsd.message('Saved', 'success')`.
- Styles: `cmnsd.css/messages.css` ([cmnsd.css](../css.md)).

## Hints while typing (hints.js)

Advice under a form that blocks nothing - "already in the archive?" under a new person's name:

```html
<div data-cmnsd-hint="/storylines/similar/" data-cmnsd-hint-fields="title"></div>
```

While the named fields are typed in (and once on load when they hold something), the address is asked with their values, and the response's `html` goes in the element. Only the latest request counts. The project writes the view.

## Single-choice toggles (toggles.js)

A group `[data-cmnsd-toggle-single]` of checkboxes, styled as buttons: pressing one releases the others, pressing it again releases it too. "At most one", where radios can't be released back to "not set". The server checks the same.

## Menus (menus.js)

A native `<details data-cmnsd-menu>` opens and closes without JavaScript. cmnsd.js closes it on a click outside, on Escape (focus back on its summary), and when another menu opens.
