# Auth

CMNSD provides a complete login/logout/registration/profile/password-reset
flow on top of Django's own `django.contrib.auth`, mounted as one URL
include. Nothing here needs models of its own — it works directly against
`auth.User` and whatever `Preferences`-like model the host project defines
(see `models.md`).

## Mounting

```python
# fmly/urls.py
urlpatterns = [
  ...
  path('accounts/', include('cmnsd.auth_urls')),
]
```

## URLs

All under `accounts/`, all named (reverse with `{% url 'login' %}` etc.):

| Name | Path | View |
|---|---|---|
| `accounts` | `accounts/` | Redirects to `profile` if authenticated, else `login` |
| `login` | `accounts/login/` | `RedirectAuthenticatedLoginView` |
| `logout` | `accounts/logout/` | `MessageLogoutView` (POST only — Django 4.1+ no longer allows GET) |
| `register` | `accounts/register/` | `register` |
| `profile` | `accounts/profile/` | `profile` |
| `password_change` | `accounts/password/` | Django's `PasswordChangeView` |
| `password_change_done` | `accounts/password/done/` | Django's `PasswordChangeDoneView` |
| `password_reset` | `accounts/password-reset/` | Django's `PasswordResetView` |
| `password_reset_done` | `accounts/password-reset/done/` | Django's `PasswordResetDoneView` |
| `password_reset_confirm` | `accounts/reset/<uidb64>/<token>/` | Django's `PasswordResetConfirmView` |
| `password_reset_complete` | `accounts/reset/done/` | Django's `PasswordResetCompleteView` |

`LOGIN_URL`/`LOGIN_REDIRECT_URL` don't need to be set explicitly — Django's
own defaults (`/accounts/login/`, `/accounts/profile/`) already match this
mount point exactly. **`LOGOUT_REDIRECT_URL` does need to be set** (see
below) — there's no equivalent lucky default for it.

## Templates

All live in `cmnsd/templates/auth/` — `login.html`, `register.html`,
`profile.html`, `password_change_form.html`, `password_change_done.html`,
`password_reset_form.html`, `password_reset_done.html`,
`password_reset_confirm.html`, `password_reset_complete.html`.

**Every one of Django's built-in auth views has its own hardcoded default
`template_name` pointing at `registration/*.html`, independent of wherever
your actual templates live.** Since these live under `auth/` instead, every
`auth_views.*View.as_view(...)` call in `auth_urls.py` passes
`template_name='auth/...'` explicitly — a built-in view used without that
kwarg silently falls back to looking for `registration/<name>.html`, which
doesn't exist here, and (depending on the view and what's installed) either
404s, 500s, or — see `LogoutView` below — silently renders someone else's
unrelated default template instead of erroring at all. If you add another
built-in Django auth view to `auth_urls.py` later, it needs the same
`template_name=` kwarg, every time — nothing catches a missing one for you.

`RedirectAuthenticatedLoginView` sets `template_name = 'auth/login.html'`
directly on the class (rather than at the URL-registration call site) since
it's a custom subclass, not used via a bare `.as_view()` call elsewhere.

## `LogoutView` needs `LOGOUT_REDIRECT_URL`

`MessageLogoutView` flashes a "You have been signed out" message via
`messages.success()` — but that only works if the response after logout is
a **redirect** to some other page render, since that's what actually
displays queued messages. Without `LOGOUT_REDIRECT_URL` set,
`LogoutView` doesn't redirect at all — it renders `registration/
logged_out.html` directly as the response. There's no template with that
name in this project, but `django.contrib.admin` ships its own fallback
`registration/logged_out.html` (a generic "Logged out | Django site admin"
page), which Django's app-dirs template loader happily finds instead —
so this doesn't error, it just silently shows the wrong, admin-branded
page, with the "signed out" message never actually seen by the user (it
sits unread in the session until whatever page they visit next).

```python
# settings.py
LOGOUT_REDIRECT_URL = '/'
```

Fixes both at once: logout now redirects (so `LogoutView` never falls
through to the admin's template), and redirecting means the flashed
message is actually rendered on arrival.

## Registration

`RegistrationForm` (`cmnsd/forms/registration.py`) extends Django's
`UserCreationForm` with `email` (required), `first_name`/`last_name`
(optional). `register()` (`cmnsd/views/auth/register.py`):

1. Builds the user via `form.save(commit=False)` (password already hashed
   at this point — `UserCreationForm` machinery), sets `is_active`, then
   saves.
2. Runs `_on_registration(user)`:
   - Adds the user to every group named in `REGISTER_DEFAULT_GROUPS`
     (skips silently if a named group doesn't exist).
   - `get_or_create`s a `Preferences`/`UserPreferences` row for them (found
     by scanning `apps.get_models()` for either name — works regardless of
     what the host project actually calls its concrete preferences model).
   - Emails `REGISTRATION_NOTIFY_EMAIL` if set (fails silently — a broken
     mail backend shouldn't block registration).
3. If the account is active, logs them in immediately and redirects to
   `?next=` or `/`. If not, shows an info message and redirects to `login`
   instead — deliberately **not** logging in an inactive account first,
   since Django's own auth backends refuse to authenticate one anyway, and
   establishing a session for a not-yet-approved user would be misleading.

### Gating registration behind approval

```python
CMNSD_REGISTRATION_REQUIRES_APPROVAL = True  # default: False
```

When `True`, new accounts are created with `is_active=False` instead of
Django's own default of `True`. This needs no further enforcement to take
effect — Django's built-in `ModelBackend.authenticate()` already refuses to
log in an inactive user, so setting this one flag is the entire mechanism.
An admin approves someone by flipping `is_active` back to `True` (the
built-in `User` admin already supports filtering/editing it; a bulk
"Approve selected users" action is easy to add the same way
`StatusAdminMixin`/`VisibilityAdminMixin` add their bulk actions — see
`admin.md` — but isn't built here, since it's User-specific, not part of a
reusable CMNSD model mixin).

This is deliberately simpler than Django's `Group`/`Permission` system:
approval is a single yes/no gate, not multiple differentiated roles, so a
boolean flag Django already enforces natively is a better fit than bundling
permissions into a group just to represent "approved or not."

## Login / Logout

`RedirectAuthenticatedLoginView` — if an already-authenticated user hits
`/accounts/login/`, they're redirected to `LOGIN_REDIRECT_URL` with an
info message instead of being shown the login form again. On success, logs
a `Login success: <user> from <ip>` line; on failure, `Login failure:
<username> from <ip>` — both via the standard `logging` module, not
`messages`.

`MessageLogoutView` — thin wrapper adding the "signed out" flash message
around Django's own `LogoutView`. POST-only, per Django 4.1+.

## Profile

`profile()` (`login_required`) renders/handles `ProfileForm` — `email`,
`first_name`, `last_name` against the `User` instance directly. Nothing
CMNSD-specific here; a project wanting to also edit its own `Preferences`
fields (e.g. `language`) on the same page would need its own form/view,
this one only touches `auth.User`'s own fields.

## Open item: read-only accounts

Template-level permission checks (`{% if perms.app.change_x %}`) are worth
adding for UX — hiding controls a user can't act on — but they enforce
nothing by themselves. A "read-only account" only actually becomes
read-only once the *views* refuse the write (`PermissionRequiredMixin` /
`@permission_required`), using Django's already-auto-created `add_*`/
`change_*`/`delete_*`/`view_*` permissions per model. Not built yet as of
this writing — the views in this project don't check permissions anywhere.
Template checks should follow view-level enforcement, not substitute for
it.
