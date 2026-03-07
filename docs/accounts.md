# Accounts

CMNSD provides a complete authentication and account management system built on top of Django's `django.contrib.auth`. All views, forms, and templates live in the local `cmnsd` app and are designed to be overridden per-project.

---

## Setup

### 1. Include the auth URLs

In your project's `urls.py`, mount cmnsd's auth URLs at `accounts/`:

```python
path('accounts/', include('cmnsd.auth_urls')),
```

### 2. Configure redirect targets

In `settings.py`:

```python
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
```

### 3. INSTALLED_APPS ordering

`cmnsd` must appear **before** `django.contrib.admin` in `INSTALLED_APPS`. Django's admin ships its own `registration/` templates (password change, reset flow) which would otherwise shadow cmnsd's templates.

```python
INSTALLED_APPS = [
    'cmnsd',
    # ... other local apps ...
    'django.contrib.admin',
    ...
]
```

### 4. Email backend (for password reset)

For development, print reset emails to the console:

```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

For production, configure SMTP via `EMAIL_HOST`, `EMAIL_PORT`, etc.

---

## URL reference

| URL | Name | Access |
|-----|------|--------|
| `accounts/login/` | `login` | Public |
| `accounts/logout/` | `logout` | Public |
| `accounts/register/` | `register` | Public (redirects if already logged in) |
| `accounts/profile/` | `profile` | Login required |
| `accounts/password/` | `password_change` | Login required |
| `accounts/password/done/` | `password_change_done` | Login required |
| `accounts/password-reset/` | `password_reset` | Public |
| `accounts/password-reset/done/` | `password_reset_done` | Public |
| `accounts/reset/<uidb64>/<token>/` | `password_reset_confirm` | Public |
| `accounts/reset/done/` | `password_reset_complete` | Public |

---

## Features

### Login — `accounts/login/`

Standard username + password form with the following behaviour:

- **`?next=` redirect** — if a user visits a protected page while unauthenticated, they are redirected to login and sent back after signing in. The navigation link appends `?next={{ request.path }}` automatically.
- **Show password toggle** — eye icon button inside the password field toggles visibility.
- **Forgot password link** — shown below the submit button, links to `password_reset`.
- **Already authenticated** — redirected to `LOGIN_REDIRECT_URL` with an info message: "You are already signed in."
- **On success** — success message: "You have been signed in."

View: `cmnsd/views/auth/login.py` — `RedirectAuthenticatedLoginView`
Template: `registration/login.html`

### Registration — `accounts/register/`

New user registration form with the following fields:

| Field | Required | Notes |
|-------|----------|-------|
| Email | Yes | Stored on the User model |
| First name | No | |
| Last name | No | |
| Username | Yes | Auto-generated from first + last name (client-side JS), editable |
| Password | Yes | Confirmed twice |

After successful registration the user is logged in automatically and redirected to `?next=` or `/`.

Form: `cmnsd/forms/registration.py` — `RegistrationForm`
View: `cmnsd/views/auth/register.py`
Template: `registration/register.html`

**Username auto-generation:** client-side JS combines first and last name, lowercases, strips accents and non-alphanumeric characters. Auto-generation stops as soon as the user manually edits the username field.

### Profile — `accounts/profile/`

Allows a logged-in user to update their email, first name and last name. Username is displayed as read-only context. On save, a success message is shown via Django's messages framework.

Form: `cmnsd/forms/profile.py` — `ProfileForm`
View: `cmnsd/views/auth/profile.py`
Template: `registration/profile.html`

### Change password — `accounts/password/`

Requires the user to enter their current password before setting a new one. On success, redirects to `accounts/password/done/` which links back to the profile page.

Template: `registration/password_change_form.html`
Done template: `registration/password_change_done.html`

### Password reset — `accounts/password-reset/`

Four-step flow for users who have forgotten their password:

1. **Enter email** — `accounts/password-reset/`
   The user submits their email address.

2. **Check your email** — `accounts/password-reset/done/`
   Shown regardless of whether the email matched an account (prevents user enumeration).

3. **Set new password** — `accounts/reset/<uidb64>/<token>/`
   Time-limited link from the email. Handles expired/invalid tokens with an inline error and a link to request a new one.

4. **Done** — `accounts/reset/done/`
   Confirmation page with a link to sign in.

---

## Overriding templates per project

All templates extend `index.html` and use neutral grey styling so they work on any project. To apply project-specific branding, create a matching template in the project's own `templates/registration/` directory — Django's template resolution will prefer it automatically.

Example for a branded login page in `cmpng`:

```
cmpng/templates/registration/login.html   ← project override (extends index.html, uses --primary etc.)
cmnsd/templates/registration/login.html   ← neutral fallback
```

---

## Files

```
cmnsd/
├── auth_urls.py
├── forms/
│   ├── registration.py      RegistrationForm
│   └── profile.py           ProfileForm
├── views/
│   └── auth/
│       ├── login.py         RedirectAuthenticatedLoginView
│       ├── register.py      register view
│       └── profile.py       profile view
└── templates/registration/
    ├── login.html
    ├── register.html
    ├── profile.html
    ├── password_change_form.html
    ├── password_change_done.html
    ├── password_reset_form.html
    ├── password_reset_done.html
    ├── password_reset_confirm.html
    └── password_reset_complete.html
```
