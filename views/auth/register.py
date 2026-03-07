from django.contrib.auth import login
from django.shortcuts import redirect, render

from cmnsd.forms import RegistrationForm


def register(request):
  if request.user.is_authenticated:
    return redirect('/')
  if request.method == 'POST':
    form = RegistrationForm(request.POST)
    if form.is_valid():
      user = form.save()
      login(request, user)
      return redirect(request.POST.get('next') or '/')
  else:
    form = RegistrationForm()
  return render(request, 'registration/register.html', {'form': form})
