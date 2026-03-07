from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.translation import gettext as _

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
  return render(request, 'registration/profile.html', {'form': form})
