from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import path

from cmnsd.views.auth.login import RedirectAuthenticatedLoginView
from cmnsd.views.auth.login_link import copy_login_link, login_link, request_login_link, revoke_login_link, send_login_link
from cmnsd.views.auth.logout import MessageLogoutView
from cmnsd.views.auth.register import register
from cmnsd.views.auth.profile import profile

urlpatterns = [
  path('', lambda request: redirect('profile' if request.user.is_authenticated else 'login'), name='accounts'),
  path('login/', RedirectAuthenticatedLoginView.as_view(), name='login'),
  # Login links (cmnsd/login_links.py) - 404 unless CMNSD_LOGIN_LINKS.
  path('login/link/', request_login_link, name='login_link_request'),
  path('login/link/send/', send_login_link, name='login_link_send'),
  path('login/link/copy/', copy_login_link, name='login_link_copy'),
  path('login/link/<int:pk>/revoke/', revoke_login_link, name='login_link_revoke'),
  path('login/link/<str:token>/', login_link, name='login_link'),
  path('logout/', MessageLogoutView.as_view(), name='logout'),
  path('register/', register, name='register'),
  path('profile/', profile, name='profile'),
  # Password change (logged-in users)
  path('password/', auth_views.PasswordChangeView.as_view(template_name='auth/password_change_form.html'), name='password_change'),
  path('password/done/', auth_views.PasswordChangeDoneView.as_view(template_name='auth/password_change_done.html'), name='password_change_done'),
  # Password reset flow
  path('password-reset/', auth_views.PasswordResetView.as_view(template_name='auth/password_reset_form.html'), name='password_reset'),
  path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='auth/password_reset_done.html'), name='password_reset_done'),
  path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='auth/password_reset_confirm.html'), name='password_reset_confirm'),
  path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='auth/password_reset_complete.html'), name='password_reset_complete'),
]
