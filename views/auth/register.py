from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.apps import apps
from django.utils.translation import gettext as _

from cmnsd.forms import RegistrationForm


def _on_registration(user):
  # Assign default groups (read + contribute; stack to allow downgrade by removing community-member)
  for group_name in getattr(settings, 'REGISTER_DEFAULT_GROUPS', []):
    try:
      user.groups.add(Group.objects.get(name=group_name))
    except Group.DoesNotExist:
      pass

  # Create preferences
  for model in apps.get_models():
    if model.__name__ in ('Preferences', 'UserPreferences'):
      model.objects.get_or_create(user=user)
      break

  # Notify admin (optional)
  notify_email = getattr(settings, 'REGISTRATION_NOTIFY_EMAIL', None)
  if notify_email:
    site_name = getattr(settings, 'SITE_NAME', 'cmnsd')
    try:
      send_mail(
        subject=f'[{site_name}] New registration: {user.username}',
        message=f'User {user.username} ({user.email}) has registered to {site_name}.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[notify_email],
        fail_silently=True,
      )
    except Exception:
      pass


def register(request):
  if request.user.is_authenticated:
    return redirect('/')
  if request.method == 'POST':
    form = RegistrationForm(request.POST)
    if form.is_valid():
      user = form.save(commit=False)
      # CMNSD_REGISTRATION_REQUIRES_APPROVAL: gate new accounts behind
      # is_active instead of the User model's own default of True - Django's
      # own auth backends already refuse to authenticate an inactive user,
      # so this needs no other enforcement to take effect.
      user.is_active = not getattr(settings, 'CMNSD_REGISTRATION_REQUIRES_APPROVAL', False)
      user.save()
      _on_registration(user)
      if user.is_active:
        login(request, user)
        return redirect(request.POST.get('next') or '/')
      messages.info(request, _('Thanks for registering - your account is pending approval before you can sign in.'))
      return redirect('login')
  else:
    form = RegistrationForm()
  return render(request, 'auth/register.html', {'form': form})
