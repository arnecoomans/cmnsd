# Templates and tags

What cmnsd ships for a project's templates: includes, template tag libraries and the two middlewares that shape every page. Markup only - the look is the project's CSS.

## Templates

| Template | What it is |
|---|---|
| `cmnsd/messages.html` | The message area: Django messages and the API's. Always rendered, so cmnsd.js has a place to put messages |
| `cmnsd/section.html` | A collapsible page section, remembered per signed-in user; a closed section is loaded only when opened. Visitors get it plain and open |
| `cmnsd/edit/*.html` | Edit mode: `block.html`, `form.html`, `choices.html`, `children.html`, `link_picker.html`, `unlink.html`, `create_form.html` ([Edit mode](edit-mode.md)) |
| `cmnsd/widgets/picker.html`, `suggest.html` | The form widgets `PickerInput` and `SuggestInput` (`forms/widgets.py`) |
| `auth/*.html` | Sign in, register, profile, password change and reset ([Accounts](accounts.md)) |
| `errorpages/*.html` | 400, 403, 404, and `private.html` for a page that exists but isn't for this viewer |
| `pages/page_detail.html` | A `Page` |

Each template's comment explains its context. A project overrides one by putting a template with the same path in its own `templates/` folder.

## Tag libraries

Load with `{% load <library> %}`, or add to `TEMPLATES` `builtins`.

| Library | Gives |
|---|---|
| `markdown` | `{{ text\|markdown }}` - markdown to HTML, sanitized with nh3: the XSS boundary for anything users write. Extensions: `CMNSD_MARKDOWN_EXTENSIONS` |
| `text_filters` | `highlight` (a match in `<mark>`), `{% highlight_search q %}...{% endhighlight_search %}` (marks search terms in rendered HTML), `get_item` (dict by variable key), `replace`, `str_replace`, `prepend`, `without_value` |
| `query_filters` | `{% update_query_params request add=... to=... %}`, `copy_query_params`, `tojson` (for an HTML attribute) |
| `queryset_filters` | `filter_by_status`, `filter_by_visibility`, `filter_by_user`, `without`, `match_queryset` |
| `list_filters` | `{% with index=people\|group_by_initial:'last_name' %}` - an A-Z index with counts, accents folded |
| `viewer_name` | `{{ obj\|viewer_name:request }}` - a name as this viewer may see it ([Access](access.md)) |
| `edit_mode` | `can_edit`, `{% edit_choices %}`, `tokens`, and helpers for child records |
| `ui_state` | `{% section_open 'storyline.chapters' as is_open %}`, `{% sections_collapsible as collapsible %}` |

Use `filter_by_status` and `filter_by_visibility` only where a queryset reaches a template unfiltered; they call the model's own rules, never a copy. Better still, filter in the view with `filter_accessible`.

## Context

From the context processors ([Installation](installation.md)):

| Variable | From |
|---|---|
| `site_name`, `meta_description`, `language_code`, `charset` | `setting_data` - the settings of the same name |
| `search_character`, `load_on_ready` | `setting_data` - `CMNSD_SEARCH_CHARACTER`, `CMNSD_LOAD_ON_READY` |
| `edit_mode`, `can_edit_mode` | `edit_mode` ([Edit mode](edit-mode.md)) |

## Middleware

- **`UserLanguageMiddleware`** (`middleware/user_language.py`) - a signed-in user's `Preferences.language`, for that request only. Without one, Django's normal detection.
- **`HtmlOutputMiddleware`** (`middleware/html_output.py`) - production pages are minified (`minify-html`); in `DEBUG` they pass unchanged, or pretty-printed with `CMNSD_DEBUG_PRETTIFY`.

## Remembered UI state

Which sections a user keeps closed and which sort order they chose are stored in `Preferences.ui_state`, keyed by name for the whole site: closing `storyline.chapters` closes it on every storyline page (`ui/state.py`). cmnsd.js saves them through `cmnsd_ui:section_state` and `cmnsd_ui:sort_state`; templates read them with the `ui_state` tags, views with `get_sort(request, key, default, allowed)`.
