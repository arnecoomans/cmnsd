from django.contrib import admin
from django.utils.translation import gettext_lazy as _


def attach_set_field_actions(cls, field_name, choices):
  """
  Attach one "Mark as <label>" bulk action per (value, label) in choices to
  cls - each sets field_name=value on the selected queryset. Shared by
  StatusAdminMixin and VisibilityAdminMixin, which both need the exact same
  "one action per choice value" mechanism, just for a different field.

  Uses queryset.update() rather than looping + save() - status/visibility
  are plain fields with no save()-time computation tied to their value
  (unlike e.g. TranslationAliasAdminMixin's action, which specifically
  needs save() to re-run), so a single UPDATE is correct and cheaper.

  Like TranslationAliasAdminMixin's action, these are NOT auto-registered
  via get_actions() - attaching them just makes them available on the
  class; the concrete ModelAdmin opts in explicitly via actions = [...].
  """
  for value, label in choices:
    def action(self, request, queryset, _value=value, _label=label):
      updated = queryset.update(**{field_name: _value})
      self.message_user(request, _("Marked %(count)d object(s) as %(label)s.") % {
        'count': updated, 'label': _label,
      })
    name = f'mark_{field_name}_{value}'
    action.__name__ = name
    setattr(cls, name, admin.action(description=_("Mark as %(label)s") % {'label': label})(action))
