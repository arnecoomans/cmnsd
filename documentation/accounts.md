# Accounts

Sign in and out, registration, profile and passwords - on Django's own `django.contrib.auth` and `auth.User`, mounted with one include. One model of its own: `LoginLink`, for login links (below, off unless turned on).

## Setup

```python
# urls.py
path('accounts/', include('cmnsd.auth_urls')),

# settings.py
LOGOUT_REDIRECT_URL = '/'
```

`LOGIN_URL` can stay at Django's default: it matches `accounts/`. So can `LOGIN_REDIRECT_URL`, but it then lands on the profile - after a sign-in without a page to return to, and a login link without one; set it to the site's home for a friendlier first page. `LOGOUT_REDIRECT_URL` can't: without it, Django renders the admin's "Logged out" page after sign-out, and the "You have been signed out" message isn't seen.

## Password guesses

Failed sign-ins are counted (`login_throttle.py`): after `CMNSD_LOGIN_ATTEMPTS_PER_ACCOUNT` (5) for one username, or `CMNSD_LOGIN_ATTEMPTS_PER_IP` (20) from one address, within `CMNSD_LOGIN_ATTEMPTS_WINDOW` (15 minutes), the next is refused before any password is checked - the right one too, until the window has passed. A success starts its account over.

- **Setup:** its backend first, Django's after it - the system check `cmnsd.auth.W001` says so when it's missing:

  ```python
  AUTHENTICATION_BACKENDS = ['cmnsd.login_throttle.ThrottleBackend', 'django.contrib.auth.backends.ModelBackend']
  ```
- **Every sign-in through `authenticate()`:** the site's form and the admin's. The form says why ("Too many attempts", and *mail yourself a login link* when those are on); the admin only that it failed.
- **By the username typed,** whether it exists or not - nothing tells who has an account. Login links and password reset don't go through it: a guesser can't lock the real user out for good.
- **The address** is `REMOTE_ADDR`, or behind a proxy the entry it added to `X-Forwarded-For` (`CMNSD_PROXY_COUNT`, counted from the right - what the client sends itself is never trusted). Unknown (gunicorn on a unix socket, no proxy count): only the account limit - never one shared count for everyone.
- **Counted in the default cache,** which has to be shared by all worker processes: a database or file cache. Django's default local-memory cache counts per process, so the limit multiplies by the workers.

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

## Login links (`CMNSD_LOGIN_LINKS`)

A mailed link that signs its user in once, instead of a password. **Off unless the project sets `CMNSD_LOGIN_LINKS = True`**: off, its pages are 404 and nothing offers it. Needs a working mail backend. Logic in `login_links.py`, model `models/LoginLink.py`, pages `views/auth/login_link.py`.

- **Invite:** staff (`is_staff` + `auth.change_user`) send it from the admin (users: the action *Send login link…*, or the button on a user's page) or a page of the project's (`login_link_send?user=<pk>&next=&back=`; fmly: its accounts page). An optional message and page to land on. Valid `CMNSD_LOGIN_LINK_INVITE_MAX_AGE` seconds (7 days). Sending again revokes the open invite.
- **Copy:** a superuser makes an invite without a mail, to pass on themselves - a chat, a text: POST `login_link_copy` (`user`, `back`; fmly: the link icon on its accounts page). The address shows once, with *copy* and, on a phone, *share*; no email address needed. Superusers only: whoever holds the link signs in as that user - a superuser may do anything already, other staff only reach someone through their own mailbox. Otherwise an invite like any other: same age, it replaces the open one, logged as *Login link copied*.
- **Request:** *Mail me a login link* on the sign-in page. The same answer whether the address is known or not; at most `CMNSD_LOGIN_LINK_REQUESTS_PER_HOUR` (3) per account. Valid `CMNSD_LOGIN_LINK_REQUEST_MAX_AGE` seconds (15 minutes); a new one revokes the earlier open request.
- **Using it:** the link opens a page with a button; only its POST signs in, so a mail scanner opening the link doesn't use it up. Once only; an inactive account (waiting for approval) never. Lands on the link's page, else `LOGIN_REDIRECT_URL`, as a password sign-in.
- **Language of the mail:** the user's chosen language (`Preferences.language`); without one, a request comes in the language the sign-in page was used in, an invite in the site's (`LANGUAGE_CODE`).
- **Rules:** any active account with an address, staff too, yourself too (another device): whoever reads someone's mail can reset their password already, so a link adds no way in. Only a SHA-256 hash of the token is stored. Every send, copy, revoke and use is in the user's admin history - never the token.
- **Revoke:** in the admin (*Login links*, or from the user's page), or by the user on their profile (*ways to sign in*).
- **Admin:** compose `LoginLinkUserAdminMixin` (`cmnsd.admin.login_links`) into the project's `UserAdmin`, before Django's.
- **Cleanup:** `manage.py login_links_cleanup` deletes used, revoked and expired links older than 30 days (`--days`).

| Name | Path | |
|---|---|---|
| `login_link_request` | `accounts/login/link/` | *Mail me a login link* |
| `login_link_send` | `accounts/login/link/send/` | Staff: send to `?user=<pk>` (several allowed) |
| `login_link_copy` | `accounts/login/link/copy/` | POST, superusers: a link for `user`, shown once |
| `login_link_revoke` | `accounts/login/link/<pk>/revoke/` | POST: its own user, or staff |
| `login_link` | `accounts/login/link/<token>/` | The mailed link |
