# Accounts

Sign in and out, registration, profile and passwords - on Django's own `django.contrib.auth` and `auth.User`, mounted with one include. No models of its own.

## Setup

```python
# urls.py
path('accounts/', include('cmnsd.auth_urls')),

# settings.py
LOGOUT_REDIRECT_URL = '/'
```

`LOGIN_URL` and `LOGIN_REDIRECT_URL` can stay at Django's defaults: they match `accounts/`. `LOGOUT_REDIRECT_URL` can't: without it, Django renders the admin's "Logged out" page after sign-out, and the "You have been signed out" message isn't seen.

## URLs

| Name | Path | |
|---|---|---|
| `accounts` | `accounts/` | To the profile when signed in, else to sign in |
| `login` | `accounts/login/` | Already signed in: redirected, with a message |
| `logout` | `accounts/logout/` | POST only (Django 5+) - a form with a button, not a link |
| `register` | `accounts/register/` | |
| `profile` | `accounts/profile/` | Email, first and last name |
| `password_change`, `..._done` | `accounts/password/` | |
| `password_reset`, `..._done`, `..._confirm`, `..._complete` | `accounts/password-reset/`, `accounts/reset/...` | Needs a working mail backend |

The templates are in `templates/auth/`. Every Django auth view in `auth_urls.py` is given its `template_name` explicitly: Django's defaults point at `registration/`, which doesn't exist here. Add a view without it and it silently finds the wrong template - or the admin's.

Sign-in and failed sign-ins are logged with the user name and IP address (`views/auth/login.py`), through Python's `logging`.

## Registration

`RegistrationForm` asks for username, email, password and an optional name (`forms/registration.py`). After saving (`views/auth/register.py`):

1. The account joins every group in `REGISTER_DEFAULT_GROUPS`.
2. A `Preferences` row is created for it.
3. `REGISTRATION_NOTIFY_EMAIL`, if set, gets a notice. A mail failure doesn't stop the registration.
4. An active account is signed in. An inactive one sees "pending approval" and isn't.

## Approval

```python
CMNSD_REGISTRATION_REQUIRES_APPROVAL = True
```

New accounts start inactive. Django already refuses to sign in an inactive user, so nothing else is needed: staff approve an account by ticking **Active** on the user in the admin.

Approval is one yes-or-no gate. What an approved account may do is decided by its groups and permissions - see [Edit mode](edit-mode.md) for how `change_*` permissions open editing.

## The profile

`profile` edits the `User`'s own fields only. A project that wants preferences (language, family) on the same page writes its own form and view for them.
