# Configuration

Every setting cmnsd reads. All are optional: cmnsd reads them with `getattr(settings, ..., default)`. The settings cmnsd needs to work at all - apps, middleware, context processors, storage - are in [Installation](installation.md).

## Site

| Setting | Default | Used for |
|---|---|---|
| `SITE_NAME` | `''` | `{{ site_name }}` in templates (`context_processors/setting_data.py`) |
| `META_DESCRIPTION` | `''` | `{{ meta_description }}` |
| `LANGUAGE_CODE`, `LANGUAGES` | Django's | `Page` languages, `Preferences.language` choices, `{{ language_code }}` |
| `LOGOUT_REDIRECT_URL` | Django's (`None`) | **Set it** (e.g. `'/'`) - see [Accounts](accounts.md) |

## Models

| Setting | Default | Used for |
|---|---|---|
| `CMNSD_DEFAULT_MODEL_STATUS` | `'p'` (published) | `StatusMixin.status` for new rows; `'c'` makes new rows concept (draft) |
| `DEFAULT_MODEL_VISIBILITY` | `'c'` (community) | `VisibilityMixin.visibility` for new rows |
| `CMNSD_VISIBILITY_FAMILY_LOOKUP_STORAGE` | `None` | The lookup path from a row to the people its owner counts as family, e.g. `'user__preferences__family'`. Without it, *family* means the owner only |
| `CMNSD_PARENT_COMPOUNDER` | `': '` | The separator `HierarchyMixin` splits names on (`"Media: Book"`) |

## Accounts

| Setting | Default | Used for |
|---|---|---|
| `CMNSD_REGISTRATION_REQUIRES_APPROVAL` | `False` | New accounts start inactive until staff activate them |
| `REGISTER_DEFAULT_GROUPS` | `[]` | Groups a new account joins (a missing group is skipped) |
| `REGISTRATION_NOTIFY_EMAIL` | `None` | Address told about each new registration |
| `DEFAULT_FROM_EMAIL` | Django's | Sender of that notice |

## Templates and output

| Setting | Default | Used for |
|---|---|---|
| `CMNSD_MARKDOWN_EXTENSIONS` | `['fenced_code', 'nl2br', 'tables', 'cmnsd.markdown.autolink:AutolinkExtension']` | The `\|markdown` filter. Add `'cmnsd.markdown.external_links:ExternalLinksExtension'` to open outside links in a new tab |
| `CMNSD_HIGHLIGHT_TAG` | `'mark'` | The element `\|highlight` wraps a match in |
| `CMNSD_SEARCH_CHARACTER` | `'q'` | The query parameter for free-text search, in the API and as `{{ search_character }}` |
| `CMNSD_LOAD_ON_READY` | `True` | `{{ load_on_ready }}`: whether templates render placeholders for deferred loading |
| `CMNSD_DEBUG_PRETTIFY` | `False` | In `DEBUG`, pretty-print pages (`HtmlOutputMiddleware`). Off by default: it puts spaces inside words around inline tags |

## Example

```python
SITE_NAME = env('SITE_NAME', default='An archive')
CMNSD_DEFAULT_MODEL_STATUS = 'c'                              # new rows start as concept
CMNSD_VISIBILITY_FAMILY_LOOKUP_STORAGE = 'user__preferences__family'
CMNSD_REGISTRATION_REQUIRES_APPROVAL = True
REGISTER_DEFAULT_GROUPS = ['Visitors']
LOGOUT_REDIRECT_URL = '/'
```

To find every setting in the code: `grep -rn "getattr(settings" cmnsd/`.
