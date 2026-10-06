from django.contrib import messages
from django.contrib.admin.models import ADDITION, LogEntry
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext as _

from cmnsd.api.registry import api_action
from cmnsd.edit.log import log_change
from cmnsd.edit.mode import require_can_edit
from cmnsd.models.access import filter_accessible


class EditableRelationsMixin(models.Model):
  """Edit a model's many-to-many relations on the page (edit mode): two
  API actions, `link` and `unlink`, for the relations the model allows -
  nothing else is reachable.

    api_editable_relations = {
      'tags': {'create': {'status': 'p', 'visibility': 'c'}},
      'people': {},
      'authors': {'path': 'book_detail.authors'},
    }

  - key: the relation's name in the API (data['relation']).
  - path: where the related manager is, if not an attribute of the same
    name (dotted - e.g. a detail model's field).
  - available: a function(obj) -> bool, for a relation that only applies
    to some objects (a book's authors, not a photo's).
  - create: the picker may create a new related object by name when
    nothing matches - only for a user with the related model's add
    permission. The dict holds the field values a new object starts with
    (e.g. published); leave 'create' out to never create.

  Both actions: the change permission on this object
  (cmnsd.edit.mode.require_can_edit), the related object must be one the
  viewer may see (filter_accessible), and the change goes to the admin
  history (cmnsd.edit.log). They return {'relation', 'object'} - the
  action template (<model>/actions/link.html) renders the new chip."""

  api_editable_relations = {}

  class Meta:
    abstract = True

  # --- helpers ---------------------------------------------------------

  def _relation(self, name):
    config = self.api_editable_relations.get(name or '')
    if config is None or not config.get('available', lambda obj: True)(self):
      raise ValidationError(_("That can't be changed here."))
    target = self
    for step in config.get('path', name).split('.'):
      target = getattr(target, step, None)
      if target is None:
        raise ValidationError(_("That can't be changed here."))
    return target, config

  def _related(self, manager, request, token):
    obj = filter_accessible(manager.model.objects.all(), request).filter(token=token or '').first()
    if obj is None:
      raise ValidationError(_("That wasn't found."))
    return obj

  @staticmethod
  def _label(obj):
    return obj._meta.verbose_name.capitalize()

  @staticmethod
  def _name(obj, request):
    """The object's name as this viewer may see it - in messages and
    errors too (an event's hidden people stay obfuscated)."""
    display = getattr(obj, 'api_display', None)
    return display(request) if display else str(obj)

  def _create_related(self, manager, config, request, name):
    """A new related object called `name` (or the visible one already
    called that), if this relation allows creating and the user may."""
    model = manager.model
    opts = model._meta
    name = (name or '').strip()
    if 'create' not in config or not name:
      raise ValidationError(_("That wasn't found."))
    if not request.user.has_perm(f'{opts.app_label}.add_{opts.model_name}'):
      raise ValidationError(_("You may not create a new %(model)s.") % {'model': opts.verbose_name})
    existing = filter_accessible(model.objects.all(), request).filter(name__iexact=name).first()
    if existing is not None:
      return existing
    fields = {'name': name, **config['create']}
    if any(field.name == 'user' for field in opts.fields):
      fields['user'] = request.user
    obj = model(**fields)
    # Validated by the model's own save() (Tag and Place run full_clean()
    # there, after deriving their slug) - a ValidationError answers 400.
    obj.save()
    LogEntry.objects.log_actions(request.user.pk, [obj], ADDITION, change_message="Created while editing", single_object=True)
    obj._just_created = True
    return obj

  # --- actions ---------------------------------------------------------

  @api_action()
  def link(self, request, data):
    """data: {relation, token} - link an existing object; or {relation,
    name} - create it first (see `create` above)."""
    require_can_edit(self, request)
    manager, config = self._relation(data.get('relation'))
    if data.get('token'):
      obj = self._related(manager, request, data.get('token'))
    else:
      obj = self._create_related(manager, config, request, data.get('name'))
    if manager.filter(pk=obj.pk).exists():
      raise ValidationError(_("%(object)s is already linked.") % {'object': self._name(obj, request)})
    manager.add(obj)
    log_change(request, self, f"Added {data['relation']}: {obj}")
    if getattr(obj, '_just_created', False):
      messages.success(request, _("%(label)s “%(object)s” created and added.") % {'label': self._label(obj), 'object': self._name(obj, request)})
    else:
      messages.success(request, _("%(label)s “%(object)s” added.") % {'label': self._label(obj), 'object': self._name(obj, request)})
    return {'relation': data['relation'], 'object': obj}

  @api_action()
  def unlink(self, request, data):
    """data: {relation, token} - remove the link; the object itself stays."""
    require_can_edit(self, request)
    manager, config = self._relation(data.get('relation'))
    obj = manager.filter(token=data.get('token') or '').first()
    if obj is None:
      raise ValidationError(_("That isn't linked."))
    manager.remove(obj)
    log_change(request, self, f"Removed {data['relation']}: {obj}")
    messages.success(request, _("%(label)s “%(object)s” removed.") % {'label': self._label(obj), 'object': self._name(obj, request)})
    return {'relation': data['relation'], 'object': obj}
