"""
Login links in the admin (cmnsd/login_links.py) - only while the project
has them on (CMNSD_LOGIN_LINKS):

- LoginLinkAdmin: every link - whose, which kind, by whom, its state - and
  "revoke" for open ones. Never the token: only its hash is stored.
- LoginLinkUserAdminMixin: for the project's UserAdmin - the action "send
  login link" (cmnsd.views.auth.send_login_link: message, page to land
  on), the same as a button on a user's page, and their links, recent
  first, with a way to revoke them.
"""

from urllib.parse import urlencode

from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _, ngettext

from cmnsd import login_links
from cmnsd.models.LoginLink import LoginLink


@admin.register(LoginLink)
class LoginLinkAdmin(admin.ModelAdmin):
  list_display = ('user', 'purpose', 'created_by', 'created_at', 'expires_at', 'state_display')
  list_filter = ('purpose',)
  search_fields = ('user__username', 'user__email')
  readonly_fields = [field.name for field in LoginLink._meta.fields if field.name not in ('id', 'token_hash')]
  exclude = ('token_hash',)
  actions = ['revoke']

  def has_module_permission(self, request):
    return login_links.enabled() and super().has_module_permission(request)

  def has_add_permission(self, request):
    return False   # made by sending one: the send page

  @admin.display(description=_("state"))
  def state_display(self, link):
    return link.get_state_display()

  @admin.action(description=_("Revoke the selected open login links"))
  def revoke(self, request, queryset):
    count = sum(login_links.revoke(link, by=request.user) for link in queryset.select_related('user'))
    self.message_user(request, ngettext("%(n)s login link revoked.", "%(n)s login links revoked.", count) % {'n': count}, messages.SUCCESS)


class LoginLinkInline(admin.TabularInline):
  model = LoginLink
  fk_name = 'user'
  fields = ('purpose', 'created_by', 'created_at', 'expires_at', 'state_display')
  readonly_fields = fields
  extra = 0
  can_delete = False
  verbose_name_plural = _("login links (revoke them under Login links)")

  @admin.display(description=_("state"))
  def state_display(self, link):
    return link.get_state_display()

  def has_add_permission(self, request, obj=None):
    return False   # made by sending one - no empty row to fill in

  def get_queryset(self, request):
    return super().get_queryset(request).select_related('created_by')


class LoginLinkUserAdminMixin:
  """For a project's UserAdmin: compose it before admin's UserAdmin."""
  actions = ['send_login_link']

  def get_actions(self, request):
    actions = super().get_actions(request)
    if not login_links.enabled():
      actions.pop('send_login_link', None)
    return actions

  def get_inlines(self, request, obj):
    inlines = list(super().get_inlines(request, obj))
    return [*inlines, LoginLinkInline] if obj and login_links.enabled() else inlines

  def get_fieldsets(self, request, obj=None):
    fieldsets = list(super().get_fieldsets(request, obj))
    if obj and login_links.enabled():
      fieldsets.append((_("login link"), {'fields': ('login_link_actions',)}))
    return fieldsets

  def get_readonly_fields(self, request, obj=None):
    return [*super().get_readonly_fields(request, obj), 'login_link_actions']

  @admin.display(description=_("login link"))
  def login_link_actions(self, user):
    send = reverse('login_link_send') + '?' + urlencode({'user': user.pk, 'back': reverse('admin:auth_user_change', args=[user.pk])})
    manage = reverse('admin:cmnsd_loginlink_changelist') + '?' + urlencode({'user__id__exact': user.pk})
    return format_html('<a class="button" href="{}">{}</a> &nbsp; <a href="{}">{}</a>', send, _("Send login link"), manage, _("Revoke a link"))

  @admin.action(description=_("Send login link…"))
  def send_login_link(self, request, queryset):
    query = [('user', pk) for pk in queryset.values_list('pk', flat=True)] + [('back', reverse('admin:auth_user_changelist'))]
    return redirect(reverse('login_link_send') + '?' + urlencode(query))
