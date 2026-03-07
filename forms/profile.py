from django import forms
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class ProfileForm(forms.ModelForm):
  email = forms.EmailField(required=True, label=_('Email address'))
  first_name = forms.CharField(required=False, label=_('First name'), max_length=150)
  last_name = forms.CharField(required=False, label=_('Last name'), max_length=150)

  class Meta:
    model = User
    fields = ('email', 'first_name', 'last_name')
