from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import path

from cmnsd.views.auth.login import RedirectAuthenticatedLoginView
from cmnsd.views.auth.logout import MessageLogoutView
from cmnsd.views.auth.register import register
from cmnsd.views.auth.profile import profile

urlpatterns = [
  path('', lambda request: redirect('profile' if request.user.is_authenticated else 'login'), name='accounts'),
  path('login/', RedirectAuthenticatedLoginView.as_view(), name='login'),
  path('logout/', MessageLogoutView.as_view(), name='logout'),
  path('register/', register, name='register'),
  path('profile/', profile, name='profile'),
  # Password change (logged-in users)
  path('password/', auth_views.PasswordChangeView.as_view(), name='password_change'),
  path('password/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
  # Password reset flow
  path('password-reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
  path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
  path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
  path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
