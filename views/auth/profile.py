from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

from cmnsd import login_links
from cmnsd.forms import ProfileForm


@login_required
def profile(request):
  if request.method == 'POST':
    form = ProfileForm(request.POST, instance=request.user)
    if form.is_valid():
      form.save()
      messages.success(request, _('Profile updated.'))
      return redirect('profile')
  else:
    form = ProfileForm(instance=request.user)
  # Ways to log in: a password or not, and open login links - each to revoke (CMNSD_LOGIN_LINKS).
  context = {'form': form, 'login_links': login_links.enabled()}
  if context['login_links']:
    context['has_password'] = request.user.has_usable_password()
    context['open_links'] = list(request.user.login_links.open().select_related('created_by'))
  return render(request, 'auth/profile.html', context)
