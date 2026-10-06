from django.contrib import admin
from django.utils.translation import gettext_lazy as _


class TranslationAliasAdminMixin:
  """Adds translation_alias to readonly_fields - it's auto-computed on
  save() from name + settings.LANGUAGES, editing it directly in the admin
  would just get overwritten on the next save anyway.

  Also offers refetch_translation_aliases as a ready-to-use bulk action
  (re-saves each selected object so its alias picks up any .po entries
  added, and compilemessages'd, since it was last saved) - but unlike the
  readonly_fields addition above, this is NOT auto-registered via
  get_actions(). An action actively mutates data in bulk for whoever has
  staff access to the changelist, so exposing it is a deliberate choice for
  the concrete ModelAdmin to make, not something a mixin should silently
  turn on. Wire it in explicitly:

    class TagAdmin(TranslationAliasAdminMixin, admin.ModelAdmin):
      actions = ['refetch_translation_aliases']
  """

  def get_readonly_fields(self, request, obj=None):
    return (*super().get_readonly_fields(request, obj), 'translation_alias')

  @admin.action(description=_("Refetch translation aliases"))
  def refetch_translation_aliases(self, request, queryset):
    # queryset.update() would bypass save() entirely, skipping the very
    # logic this action exists to re-run - each object needs a real save().
    for obj in queryset:
      obj.save()
    self.message_user(request, _("Refreshed translation aliases for %(count)d object(s).") % {'count': queryset.count()})
