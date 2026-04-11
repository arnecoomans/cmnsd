from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.text import capfirst


class ReadOnlyAdmin(admin.ModelAdmin):
  """Admin that makes all fields read-only and disables add/delete."""
  readonly_fields = []

  def get_readonly_fields(self, request, obj=None):
    return list(self.readonly_fields) + \
      [field.name for field in obj._meta.fields] + \
      [field.name for field in obj._meta.many_to_many]

  def has_add_permission(self, request):
    return False

  def has_delete_permission(self, request, obj=None):
    return False


class BaseModelAdmin(admin.ModelAdmin):
  """Admin mixin for models inheriting from BaseModel.

  Adds token/date readonly fields, a collapsed system info fieldset,
  auto-assigns the current user on creation, and a recalculate action.
  """

  actions = ['recalculate_fields']
  readonly_fields = ('token', 'date_created', 'date_modified')

  def save_model(self, request, obj, form, change):
    if not change and not obj.user:
      obj.user = request.user
    super().save_model(request, obj, form, change)

  def get_fieldsets(self, request, obj=None):
    fieldsets = super().get_fieldsets(request, obj)
    fieldsets += (
      (capfirst(_('system information')), {
        'classes': ('collapse',),
        'fields': ('token', 'status', 'user', 'date_created', 'date_modified'),
      }),
    )
    return fieldsets

  @admin.action(description=_('Recalculate computed fields (run save on selected items)'))
  def recalculate_fields(self, request, queryset):
    count = 0
    for obj in queryset:
      obj.save()
      count += 1
    self.message_user(
      request,
      _(f'Successfully recalculated {count} {queryset.model._meta.verbose_name_plural}.'),
    )


class VisibilityModelAdmin(admin.ModelAdmin):
  """Admin mixin for models inheriting from VisibilityModel.

  Adds a collapsed Visibility fieldset. Combine with BaseModelAdmin:

    class MyAdmin(VisibilityModelAdmin, BaseModelAdmin):
        ...
  """

  def get_fieldsets(self, request, obj=None):
    fieldsets = super().get_fieldsets(request, obj)
    already_included = any(
      'visibility' in (fields.get('fields') or ())
      for _, fields in fieldsets
    )
    if not already_included:
      fieldsets += (
        (capfirst(_('visibility')), {
          'classes': ('collapse',),
          'fields': ('visibility',),
        }),
      )
    return fieldsets


class TranslationAliasAdminMixin(admin.ModelAdmin):
  """Admin mixin for models using TranslationAliasMixin.

  Adds aliases as a collapsed read-only fieldset.
  """

  def get_readonly_fields(self, request, obj=None):
    readonly = list(super().get_readonly_fields(request, obj))
    if 'aliases' not in readonly:
      readonly.append('aliases')
    return tuple(readonly)

  def get_fieldsets(self, request, obj=None):
    fieldsets = list(super().get_fieldsets(request, obj))
    already_included = any(
      'aliases' in (fields.get('fields') or ())
      for _, fields in fieldsets
    )
    if not already_included:
      fieldsets.append((
        capfirst(_('translation aliases')), {
          'fields': ('aliases',),
          'classes': ('collapse',),
          'description': capfirst(_(
            'auto-populated from .po translations on save. '
            'run update_translation_aliases after compilemessages.'
          )),
        }
      ))
    return fieldsets
