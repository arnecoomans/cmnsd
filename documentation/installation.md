# Installation

How to add cmnsd to a Django 6 project (Python 3.12 or later). cmnsd is a git submodule, not a package.

## The submodule

```sh
git submodule add -b <branch> https://github.com/arnecoomans/cmnsd.git cmnsd
```

The branch is what the project follows: `update.sh` brings it to the newest commit of that branch on every deploy ([Resources](resources.md)). Use a branch of the project's own - `fmly` for FMLY3 - and move it to a new cmnsd only on purpose. To clone a project that already has cmnsd: `git clone --recurse-submodules ...`, or `git submodule update --init` afterwards.

Include cmnsd's requirements in the project's `requirements.txt`, so one install covers both - `update.sh` installs only the project's file:

```
-r cmnsd/requirements.txt
```

## Settings

```python
INSTALLED_APPS = [
  ...
  'cmnsd',
]

MIDDLEWARE = [
  ...
  'django.contrib.auth.middleware.AuthenticationMiddleware',
  'cmnsd.middleware.user_language.UserLanguageMiddleware',    # after authentication
  'django.contrib.messages.middleware.MessageMiddleware',
  ...
  'cmnsd.middleware.html_output.HtmlOutputMiddleware',        # last: minifies the finished page
]

TEMPLATES = [{
  ...
  'OPTIONS': {
    'context_processors': [
      ...
      'django.template.context_processors.request',          # cmnsd's templates need the request
      'cmnsd.context_processors.setting_data.setting_data',  # site_name, meta_description, ...
      'cmnsd.context_processors.edit_mode.edit_mode',        # edit_mode, can_edit_mode
    ],
  },
}]

STORAGES = {
  'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
  'staticfiles': {'BACKEND': 'cmnsd.storage.ManifestStaticFilesStorage'},
}

LOGOUT_REDIRECT_URL = '/'
```

While testing, use Django's plain `StaticFilesStorage`: there's no collected manifest to look names up in. See [Static files](static-files.md). The other settings, all optional: [Configuration](configuration.md).

## Models

cmnsd has one table of its own (`Page`) and abstract models for the rest. A project defines its concrete `Preferences` (required: the language middleware and remembered UI state read `user.preferences`), and usually `Tag` and `Comment`, in a `core` app. See [Models](models.md).

```sh
python manage.py migrate
```

## URLs

```python
urlpatterns = [
  path('api/', include('cmnsd.api_urls')),        # the API - cmnsd.js's apiRoot
  path('accounts/', include('cmnsd.auth_urls')),  # sign in, register, profile, passwords
  path('ui/', include('cmnsd.ui_urls')),          # edit-mode switch, remembered sections and sort orders
  path('pages/', include('cmnsd.urls')),          # Page: the cookie statement and its kind
  ...
]

handler400 = 'cmnsd.views.errors.bad_request'
handler403 = 'cmnsd.views.errors.permission_denied'
handler404 = 'cmnsd.views.errors.page_not_found'
```

## The base template

The project writes its own `base.html`. cmnsd needs three things in it: the CSRF meta tag for signed-in users, the message area (`{% include 'cmnsd/messages.html' %}` with `cmnsd.css/messages.css`), and cmnsd.js started with `cmnsd.init(...)`. The snippet: [cmnsd.js](javascript/readme.md#setup).

## Check

```sh
python manage.py check
```

cmnsd's system checks catch API registration mistakes at startup: a registered model without a token or slug (`cmnsd.api.E001`), a search field that isn't a text field (`cmnsd.api.E002`), a relation exposed directly (`cmnsd.api.W001`). See `checks/ApiChecks.py`.
