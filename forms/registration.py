from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class RegistrationForm(UserCreationForm):
  email = forms.EmailField(required=True, label=_('Email address'), widget=forms.EmailInput(attrs={'autofocus': True}))
  first_name = forms.CharField(required=False, label=_('First name'), max_length=150)
  last_name = forms.CharField(required=False, label=_('Last name'), max_length=150)

  class Meta:
    model = User
    fields = ('email', 'first_name', 'last_name', 'username', 'password1', 'password2')
    widgets = {
      'username': forms.TextInput(attrs={'autofocus': False}),
    }

  def save(self, commit=True):
    user = super().save(commit=False)
    user.email = self.cleaned_data['email']
    user.first_name = self.cleaned_data.get('first_name', '')
    user.last_name = self.cleaned_data.get('last_name', '')
    if commit:
      user.save()
    return user
