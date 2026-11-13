"""
Login links (cmnsd/login_links.py) - the pages:

- login_link: the mailed link. GET shows a page with a button; only its
  POST logs in - a mail scanner opening the link doesn't use it up. A used,
  revoked or expired link says which, with the way forward - unless it's
  the signed-in user's own: then on to where it leads, no error.
- request_login_link: "mail me a login link" on the login page - the same
  answer whether the address is known or not.
- send_login_link: staff mail one or more users a link (an invite), with
  an optional message and page to land on - from the admin's user action
  or a person's page (?user=<pk>&user=...&next=...&back=...).
- copy_login_link: a superuser makes a link to pass on themselves (a
  chat, a text) - shown once, with copy and share.
- revoke_login_link: revoke one open link - its own user, or staff.

All 404 while the project hasn't turned login links on (CMNSD_LOGIN_LINKS).
"""

import logging

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _, gettext_lazy
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from cmnsd import login_links
from cmnsd.login_throttle import client_ip
from cmnsd.models.LoginLink import LoginLink

logger = logging.getLogger(__name__)


def _require_enabled():
  if not login_links.enabled():
    raise Http404


def _home():
  return getattr(settings, 'LOGIN_REDIRECT_URL', '/') or '/'


def login_link(request, token):
  _require_enabled()
  link = login_links.find(token)
  valid = link is not None and link.is_valid()
  if request.method == 'POST' and valid:
    login_links.use(request, link)
    messages.success(request, _('You have been signed in.'))
    logger.info(f"Login link used: {link.user} from {client_ip(request)}")
    return redirect(login_links.safe_next(link.next, request) or _home())
  if not valid and link is not None and request.user.is_authenticated and link.user_id == request.user.pk:
    # Their own link, opened again (a second click, the back button): they're
    # in already - nothing to report, on to where it leads.
    messages.info(request, _('You are already signed in.'))
    return redirect(login_links.safe_next(link.next, request) or _home())
  if request.method == 'POST':
    logger.warning(f"Login link refused ({link.state if link else 'unknown'}) from {client_ip(request)}")
  # Not valid: why - an unknown token reads as expired, nothing more to tell.
  state = 'open' if valid else (link.state if link and link.state != 'open' else 'expired')
  context = {
    'link': link if valid else None, 'state': state,
    'signed_in_as': request.user if request.user.is_authenticated else None,
  }
  return render(request, 'auth/login_link.html', context, status=200 if valid else 410)


class RequestForm(forms.Form):
  email = forms.EmailField(label=gettext_lazy("email address"), widget=forms.EmailInput(attrs={'autocomplete': 'email', 'autofocus': True}))


def request_login_link(request):
  """Mail a login link to an active account with this address - at most
  CMNSD_LOGIN_LINK_REQUESTS_PER_HOUR per account. The answer is the same
  whether the address is known, refused or sent: it never tells who has
  an account."""
  _require_enabled()
  if request.user.is_authenticated:
    return redirect(_home())
  next_url = login_links.safe_next(request.POST.get('next') or request.GET.get('next') or '', request)
  form = RequestForm(request.POST or None)
  if request.method == 'POST' and form.is_valid():
    users = get_user_model().objects.filter(email__iexact=form.cleaned_data['email'], is_active=True)
    for user in users:
      if login_links.requested_recently(user) >= login_links.requests_per_hour():
        logger.warning(f"Login link request over the limit: {user} from {client_ip(request)}")
        continue
      try:
        login_links.send(request, user, LoginLink.Purpose.REQUEST, next_url=next_url)
      except Exception:
        logger.exception(f"Login link request: mail to {user} failed")
    return render(request, 'auth/login_link_request.html', {'sent': True, 'email': form.cleaned_data['email']})
  return render(request, 'auth/login_link_request.html', {'form': form, 'next': next_url})


class SendForm(forms.Form):
  message = forms.CharField(
    label=gettext_lazy("personal message"), required=False, widget=forms.Textarea(attrs={'rows': 4}),
    help_text=gettext_lazy("Optional - in the mail, above the link."),
  )
  next = forms.CharField(
    label=gettext_lazy("page to land on"), required=False,
    help_text=gettext_lazy("Optional - an address on this site, e.g. a photo you want them to see."),
  )


def send_login_link(request):
  """Staff (auth.change_user): mail the chosen users (?user=<pk>, several
  allowed) an invite - each checked on its own (login_links.refusal): a
  an address needed, an active account.
  GET: who it goes to, why not for some, the form. POST: sent, back to
  `back` (an internal path) or the admin's user list."""
  _require_enabled()
  if not (request.user.is_authenticated and request.user.is_staff and request.user.has_perm('auth.change_user')):
    raise Http404
  data = request.POST if request.method == 'POST' else request.GET
  ids = [pk for pk in data.getlist('user') if pk.isdigit()]
  recipients = list(get_user_model().objects.filter(pk__in=ids).select_related('preferences').order_by('username'))
  if not recipients:
    raise Http404
  for recipient in recipients:
    recipient.refusal = login_links.refusal(request.user, recipient)
    recipient.open_invites = recipient.login_links.open().filter(purpose=LoginLink.Purpose.INVITE).count()
  back = login_links.safe_next(data.get('back', ''), request)
  form = SendForm(request.POST or None, initial={'next': data.get('next', '')})
  if request.method == 'POST' and form.is_valid():
    sent, failed = [], []
    for recipient in recipients:
      if recipient.refusal:
        continue
      try:
        login_links.send(request, recipient, LoginLink.Purpose.INVITE, sender=request.user, message=form.cleaned_data['message'], next_url=form.cleaned_data['next'])
        sent.append(recipient)
      except Exception:
        logger.exception(f"Login link to {recipient} failed")
        failed.append(recipient)
    if sent:
      messages.success(request, _("Login link sent to %(names)s.") % {'names': ', '.join(masked(user.email) for user in sent)})
    if failed:
      messages.error(request, _("Not sent - the mail couldn't be delivered: %(names)s.") % {'names': ', '.join(str(user) for user in failed)})
    return redirect(back or 'admin:auth_user_changelist')
  return render(request, 'auth/login_link_send.html', {
    'form': form, 'recipients': recipients, 'back': back,
    'can_send': any(not recipient.refusal for recipient in recipients),
    'max_age_days': login_links.max_age(LoginLink.Purpose.INVITE).days,
  })


@require_POST
@never_cache
def copy_login_link(request):
  """A superuser (login_links.may_copy): a new invite for `user`, not
  mailed - its address on a page, once, to copy or share. Refused (not
  active): back to `back` with why."""
  _require_enabled()
  if not login_links.may_copy(request.user):
    raise Http404
  user = get_object_or_404(get_user_model(), pk=request.POST.get('user') if (request.POST.get('user') or '').isdigit() else None)
  back = login_links.safe_next(request.POST.get('back', ''), request)
  refusal = login_links.copy_refusal(request.user, user)
  if refusal:
    messages.error(request, _("No login link for %(name)s: %(why)s.") % {'name': user, 'why': refusal})
    return redirect(back or 'admin:auth_user_changelist')
  link, url = login_links.copy(request, user, request.user)
  logger.info(f"Login link copied for {user} by {request.user}")
  return render(request, 'auth/login_link_copy.html', {'link': link, 'url': url, 'back': back})


def masked(email):
  """j***@example.com - enough to recognise, not to copy."""
  name, _at, domain = email.partition('@')
  return f"{name[:1]}***@{domain}" if domain else '***'


@require_POST
def revoke_login_link(request, pk):
  """Revoke one open link - by its own user (their profile) or staff
  (auth.change_user). Back to `back` or the profile."""
  _require_enabled()
  if not request.user.is_authenticated:
    raise Http404
  link = get_object_or_404(LoginLink, pk=pk)
  if link.user_id != request.user.pk and not (request.user.is_staff and request.user.has_perm('auth.change_user')):
    raise Http404
  if login_links.revoke(link, by=request.user):
    messages.success(request, _("Login link revoked."))
  return redirect(login_links.safe_next(request.POST.get('back', ''), request) or 'profile')
