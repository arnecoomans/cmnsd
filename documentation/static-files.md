# Static files

cmnsd ships the front-end libraries and fonts its projects use, so a page loads nothing from other sites. And it stores collected files under hashed names, so a browser never keeps running an old copy.

## What's included

All under `static/`, each in a folder named with its version and a symlink without one. Templates use the symlink, so an upgrade is: add the new folder, move the link.

| Library | Folder | Link |
|---|---|---|
| Bootstrap 5.3.8 | `css/bootstrap-5.3.8/`, `js/bootstrap-5.3.8/` | `css/bootstrap/`, `js/bootstrap/` |
| Bootstrap Icons 1.13.1 | `css/bootstrap-icons-1.13.1/` (stylesheet), `fonts/bootstrap-icons/` (font), `images/bootstrap-icons-1.13.1/` (SVGs) | `css/bootstrap-icons/`, `images/bootstrap-icons/` |
| jQuery 3.7.1 | `js/jquery-3.7.1/` | `js/jquery/` |
| jQuery UI 1.14.1 | `js/jquery-ui-1.14.1/` | `js/jquery-ui/` |
| Inter | `fonts/inter/` | |
| Geist and Geist Mono 1.8.0 | `fonts/geist-font-1.8.0/` | |

cmnsd's own files: `cmnsd.js/` ([cmnsd.js](javascript/readme.md)) and `cmnsd.css/` ([cmnsd.css](css.md)). cmnsd.js needs neither jQuery nor Bootstrap; they're here for the projects' own pages.

```django
<link rel="stylesheet" href="{% static 'css/bootstrap/bootstrap.min.css' %}">
<link rel="stylesheet" href="{% static 'css/bootstrap-icons/bootstrap-icons.css' %}">
<img src="{% static 'images/bootstrap-icons/github.svg' %}" alt="GitHub">
```

**Adding a library:** only what pages load. A package's extras - its own stylesheet next to the images, source maps for files nobody uses - end up being processed and served. The icon stylesheet points at `../../fonts/bootstrap-icons/`, so the font lives in `fonts/`, not next to the CSS.

## Hashed file names

```python
STORAGES = {
  ...
  'staticfiles': {'BACKEND': 'cmnsd.storage.ManifestStaticFilesStorage'},
}
```

`collectstatic` stores each file with its content hash in the name (`cmnsd.js/viewer.3f2a1c9e0b4d.js`) and `{% static %}` links to that name. A changed file gets a new name; an unchanged one can be cached for good.

On top of Django's `ManifestStaticFilesStorage` (`storage.py`):

- **ES module imports are rewritten too** (`import { request } from './api.js'`), or a module would load its neighbours under their plain, cacheable names.
- **A reference to a file that doesn't exist** - inside a vendored stylesheet - is left as it is and logged as a warning ("Static file reference not found, left unhashed"), instead of stopping `collectstatic`. It was broken already. A template's `{% static %}` of a missing file still fails.

`collectstatic` must run on every deploy: without it pages fail with "Missing staticfiles manifest entry". `update.sh` always runs it ([Resources](resources.md)).

## Development and tests

With `DEBUG` on, `{% static %}` keeps plain names and `runserver` serves the files as they are; no `collectstatic` needed. A browser may still cache an old script: hard reload, or disable the cache in the developer tools.

Tests use Django's plain `StaticFilesStorage`, since there's no manifest:

```python
STORAGES['staticfiles']['BACKEND'] = (
  'django.contrib.staticfiles.storage.StaticFilesStorage' if TESTING
  else 'cmnsd.storage.ManifestStaticFilesStorage'
)
```
