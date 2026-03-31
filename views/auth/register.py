from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.shortcuts import redirect, render

from cmnsd.forms import RegistrationForm


def _on_registration(user):
  # Assign default groups (read + contribute; stack to allow downgrade by removing community-member)
  for group_name in ('community-member-read', 'community-member'):
    try:
      user.groups.add(Group.objects.get(name=group_name))
    except Group.DoesNotExist:
      pass

  # Create preferences
  from locations.models.Preferences import UserPreferences
  UserPreferences.objects.get_or_create(user=user)

  # Notify admin (optional)
  notify_email = getattr(settings, 'REGISTRATION_NOTIFY_EMAIL', None)
  if notify_email:
    site_name = getattr(settings, 'SITE_NAME', 'cmpng')
    try:
      send_mail(
        subject=f'[{site_name}] New registration: {user.username}',
        message=f'User {user.username} ({user.email}) has registered.',
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
      user = form.save()
      _on_registration(user)
      login(request, user)
      return redirect(request.POST.get('next') or '/')
  else:
    form = RegistrationForm()
  return render(request, 'registration/register.html', {'form': form})
