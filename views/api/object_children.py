from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.urls import reverse
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from cmnsd.edit.log import log_change

from .lookup import get_visible_object, resolve_model
from .object_form import MODIFIED_FIELD, _modified, _render, form_html
from .response import api_response, api_view


# --- what a model declares -------------------------------------------------

def child_config(owner, relation):
  """The owner's api_editable_children entry for `relation`, else Http404:
    api_editable_children = {'transcripts': {'form': 'content.forms.TranscriptForm'}}
  `relation` is the reverse foreign key's name (owner.transcripts)."""
  config = (getattr(owner, 'api_editable_children', {}) or {}).get(relation)
  if config is None:
    raise Http404(f"'{relation}' can't be edited here.")
  return config


def child_manager(owner, relation):
  return getattr(owner, relation)


def child_permissions(user, owner, relation):
  """{'add', 'change', 'delete'}: the child model's own Django permissions
  (e.g. content.change_transcript) - separate from editing the owner."""
  model = child_manager(owner, relation).model
  opts = model._meta
  ok = bool(user and user.is_authenticated and user.is_active)
  return {action: ok and user.has_perm(f'{opts.app_label}.{action}_{opts.model_name}') for action in ('add', 'change', 'delete')}


def _form_class(config):
  form = config['form']
  return import_string(form) if isinstance(form, str) else form


def child_urls(model, owner, relation, child=None):
  """The endpoints for a relation (add) or a child (edit, delete) - and,
  when the relation is edited on a page of its own (config 'page': a
  function(owner, child_or_None) -> URL, e.g. a transcribe page), that
  page as add_page / edit_page: the pencil and "+ add" then go there
  instead of opening a form in place."""
  config = child_config(owner, relation)
  page = config.get('page')
  base = reverse('cmnsd_api:object_children', args=[model, owner.token, relation])
  if child is None:
    urls = {'add': base}
    if page:
      urls['add_page'] = page(owner, None)
    return urls
  item = reverse('cmnsd_api:object_child', args=[model, owner.token, relation, child.pk])
  urls = {'edit': item, 'delete': reverse('cmnsd_api:object_child_delete', args=[model, owner.token, relation, child.pk])}
  if page:
    urls['edit_page'] = page(owner, child)
  return urls


# --- rendering ------------------------------------------------------------------

def child_context(model, owner, relation, request, child=None):
  return {
    model: owner, 'obj': owner, 'model': model, 'relation': relation, 'child': child,
    'perms_child': child_permissions(request.user, owner, relation), 'request': request,
  }


def child_html(model, owner, relation, child, request):
  """One child as the page shows it (cmnsd/edit/child.html around
  <model>/children/<relation>.html) - the same template the page uses."""
  return _render(['cmnsd/edit/child.html'], child_context(model, owner, relation, request, child), request)


def add_html(model, owner, relation, request):
  return _render(['cmnsd/edit/child_add.html'], child_context(model, owner, relation, request), request)


def _form(model, owner, relation, form, action, child, request):
  return form_html(
    [f'{model}/children/{relation}_form.html'], form, action, _modified(child) if child else '', request,
    **{model: owner, 'obj': owner, 'model': model, 'relation': relation, 'child': child},
  )


def _validate_constraints(form):
  """The form leaves out the owner field (it's set from the URL), so Django
  skips the constraints that involve it - e.g. one transcript per
  language. Checked here, so a clash is a form error, not a database
  error."""
  try:
    form.instance.validate_constraints()
  except ValidationError as error:
    form.add_error(None, error)
  return form.is_valid()


# --- endpoints ------------------------------------------------------------------

@api_view
@require_http_methods(['GET', 'POST'])
def object_children(request, model, identifier, relation):
  """api/<model>/<token>/children/<relation>/ - a new child record of a
  visible object (edit mode; cmnsd.js edit.js). GET: the empty form. POST:
  create it - the response's `html` is the new child plus a fresh "+ add",
  which replace the old "+ add" on the page (cmnsd/edit/child_add.html).
  Needs the child model's add permission."""
  model_cls, entry = resolve_model(model)
  owner = get_visible_object(request, model_cls, entry, identifier)
  config = child_config(owner, relation)
  if not child_permissions(request.user, owner, relation)['add']:
    return api_response(request, status=403, entry=entry, obj=owner, error=_("You may not add this."), errors={'permission': True})
  manager = child_manager(owner, relation)
  instance = manager.model(**{manager.field.name: owner})
  form_class = _form_class(config)
  action = child_urls(model, owner, relation)['add']
  if request.method == 'GET':
    return api_response(request, entry=entry, obj=owner, html=_form(model, owner, relation, form_class(instance=instance, prefix=relation), action, None, request))
  form = form_class(request.POST, instance=instance, prefix=relation)
  if not (form.is_valid() and _validate_constraints(form)):
    return api_response(
      request, status=400, entry=entry, obj=owner, html=_form(model, owner, relation, form, action, None, request),
      error=_("Please correct the errors in the form."), errors={'validation': form.errors.get_json_data()},
    )
  child = form.save()
  label = child._meta.verbose_name
  log_change(request, owner, f"Added {label}: {child}")
  messages.success(request, _("%(label)s added.") % {'label': label.capitalize()})
  # `child`: where the new record now lives and its version - so a form
  # that keeps saving (cmnsd.js autosave.js) continues on it.
  return api_response(
    request, entry=entry, obj=owner,
    html=child_html(model, owner, relation, child, request) + add_html(model, owner, relation, request),
    child={'id': child.pk, **child_urls(model, owner, relation, child)}, modified=_modified(child),
  )


@api_view
@require_http_methods(['GET', 'POST'])
def object_child(request, model, identifier, relation, child_id):
  """api/<model>/<token>/children/<relation>/<id>/ - one child record.
  GET: its form; POST: save it - `html` is the updated child. Needs the
  child model's change permission; the child is looked up among this
  owner's own (another owner's id is a 404). Stale check (409) on the
  child's date_modified, like blocks."""
  model_cls, entry = resolve_model(model)
  owner = get_visible_object(request, model_cls, entry, identifier)
  config = child_config(owner, relation)
  child = child_manager(owner, relation).filter(pk=child_id).first()
  if child is None:
    raise Http404("No such child.")
  if not child_permissions(request.user, owner, relation)['change']:
    return api_response(request, status=403, entry=entry, obj=owner, error=_("You may not change this."), errors={'permission': True})
  form_class = _form_class(config)
  action = child_urls(model, owner, relation, child)['edit']
  if request.method == 'GET':
    return api_response(request, entry=entry, obj=owner, html=_form(model, owner, relation, form_class(instance=child, prefix=relation), action, child, request))
  if request.POST.get(MODIFIED_FIELD, '') != _modified(child):
    return api_response(
      request, status=409, entry=entry, obj=owner, errors={'stale': True},
      error=_("This was changed by someone else since you opened it - reload the page to see the new version."),
    )
  form = form_class(request.POST, instance=child, prefix=relation)
  if not (form.is_valid() and _validate_constraints(form)):
    return api_response(
      request, status=400, entry=entry, obj=owner, html=_form(model, owner, relation, form, action, child, request),
      error=_("Please correct the errors in the form."), errors={'validation': form.errors.get_json_data()},
    )
  changed = form.changed_data
  child = form.save()
  if changed:
    log_change(request, owner, f"Changed {child._meta.verbose_name} ({child}): {', '.join(changed)}")
    messages.success(request, _("Saved."))
  return api_response(request, entry=entry, obj=owner, html=child_html(model, owner, relation, child, request), modified=_modified(child))


@api_view
@require_POST
def object_child_delete(request, model, identifier, relation, child_id):
  """api/<model>/<token>/children/<relation>/<id>/delete/ - remove a child
  record (the page asks first). `removed` tells edit.js to take its block
  away. Needs the child model's delete permission."""
  model_cls, entry = resolve_model(model)
  owner = get_visible_object(request, model_cls, entry, identifier)
  child_config(owner, relation)
  child = child_manager(owner, relation).filter(pk=child_id).first()
  if child is None:
    raise Http404("No such child.")
  if not child_permissions(request.user, owner, relation)['delete']:
    return api_response(request, status=403, entry=entry, obj=owner, error=_("You may not remove this."), errors={'permission': True})
  label, text = child._meta.verbose_name, str(child)
  child.delete()
  log_change(request, owner, f"Removed {label}: {text}")
  messages.success(request, _("%(label)s removed.") % {'label': label.capitalize()})
  return api_response(request, entry=entry, obj=owner, removed=True)
