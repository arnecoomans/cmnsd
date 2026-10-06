import minify_html

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.template.loader import render_to_string, select_template
from django.utils.module_loading import import_string
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from cmnsd.api.filtering import visible_queryset
from cmnsd.edit.log import log_change
from cmnsd.edit.mode import require_can_edit

from .lookup import get_visible_object, resolve_model
from .response import api_response, api_view

# The hidden field a block form carries: the object's date_modified when the
# form was opened. A save is refused if the object changed since - nobody
# silently overwrites someone else's edit.
MODIFIED_FIELD = '_modified'


def _form_class(obj, name):
  """The form for block `name`: the model's api_edit_forms entry - a form
  class or its dotted path (a model can't import its own forms module)."""
  forms = getattr(obj, 'api_edit_forms', {}) or {}
  form_class = forms.get(name)
  if form_class is None:
    raise Http404(f"'{name}' is not an editable block.")
  return import_string(form_class) if isinstance(form_class, str) else form_class


def instance_for(form_class, obj):
  """What the block's form edits: the object itself, or - when the form
  class defines instance_for(obj) - a related record, e.g. an item's
  photo details. History, messages and the stale check stay on obj."""
  hook = getattr(form_class, 'instance_for', None)
  return hook(obj) if hook else obj


def make_form(form_class, request, *args, **kwargs):
  """The form, with `request` set - and its prepare() called if it has
  one: the place to add fields that depend on the request or the query
  (e.g. a new child's other parent, from the partners the viewer may see;
  a portrait's photos, from those the viewer may see). Used by the block
  forms here and by object_create.
  Also before validation, so a POST sees the same fields."""
  form = form_class(*args, **kwargs)
  form.request = request
  prepare = getattr(form, 'prepare', None)
  if prepare:
    prepare()
  return form


def _modified(obj):
  value = getattr(obj, 'date_modified', None)
  return value.isoformat() if value else ''


def _render(template_names, context, request):
  html = select_template(template_names).render(context, request)
  return minify_html.minify(html, minify_js=True, minify_css=True)


def block_html(entry, obj, name, request):
  """The block as the page shows it: cmnsd/edit/block.html around
  <model>/blocks/<name>.html - the same include the page uses."""
  context = {
    entry['name']: obj, 'obj': obj, 'model': entry['name'], 'block': name, 'request': request,
    # a choice block saves on click - no pencil (see cmnsd/edit/choices.html)
    'choice': getattr(_form_class(obj, name), 'choice', False),
    # an extra class on the wrapper, e.g. a wide row - the page passes the same
    'block_class': getattr(_form_class(obj, name), 'block_class', ''),
    # edits in a dialog (cmnsd.js edit.js) - the page passes the same
    'dialog': getattr(_form_class(obj, name), 'dialog_title', ''),
  }
  return _render(['cmnsd/edit/block.html'], context, request)


def form_html(template_names, form, action, modified, request, **context):
  """A block form rendered for edit.js: `form_action` (where it posts) and
  the stale-check field (`modified`) - shared by blocks and child records
  (object_children)."""
  context.update({
    'form': form, 'form_action': action, 'modified': modified,
    'modified_field': MODIFIED_FIELD, 'request': request,
  })
  return _render([*template_names, 'cmnsd/edit/form.html'], context, request)


def _form_html(entry, obj, name, form, request):
  return form_html(
    [f"{entry['name']}/forms/{name}.html"], form,
    reverse('cmnsd_api:object_form', args=[entry['name'], obj.token, name]), _modified(obj), request,
    **{entry['name']: obj, 'obj': obj, 'model': entry['name'], 'block': name},
  )


@api_view
@require_http_methods(['GET', 'POST'])
def object_form(request, model, identifier, name):
  """api/<model>/<token>/form/<name>/ - edit one block of fields in place
  (edit mode; cmnsd.js edit.js).

  GET: the block's form (<model>/forms/<name>.html, else the generic
  cmnsd/edit/form.html) as `html`. POST: validate with the model's form -
  its own clean() included; valid: save, log the changed fields to the
  admin history, queue "Saved", and return the updated block (`html`, and
  `url` - the object's address, which can change with its name); invalid:
  400 with the form and its errors. Both need the change permission on
  the object (cmnsd.edit.mode); the object must be visible to the viewer
  (else 404). A save is refused (409) when the object changed since the
  form was opened.

  A form class may also say:
  - instance_for(obj): edit a related record (an item's photo details);
  - prepare(): called with form.request set (make_form), to add fields
    that depend on the viewer;
  - choice = True: a choice block - buttons that save on click
    (cmnsd/edit/choices.html), no pencil;
  - reload_page = True: the change affects more of the page (an item's
    kind) - the response says `reload`;
  - dialog_title = '...': the block edits in a dialog with that title
    (cmnsd.js edit.js), e.g. a portrait crop;
  - confirm = {value: question}: ask before saving that value (a choice
    block, e.g. status "deleted");
  - success_message(): the message instead of "Saved." ('' = default);
  - actions(user): [(value, label), ...] - an action block: buttons named
    after what they do ("Publish", "Revoke") instead of every choice; the
    form itself must refuse a value it doesn't offer (form.request is set
    before validation).
  When the object is no longer visible to the viewer after the save (its
  status set to deleted), the response says `redirect` - its
  get_list_url(), else '/'."""
  model_cls, entry = resolve_model(model)
  obj = get_visible_object(request, model_cls, entry, identifier)
  try:
    require_can_edit(obj, request)
  except PermissionDenied as error:
    return api_response(request, status=403, entry=entry, obj=obj, error=str(error), errors={'permission': True})
  form_class = _form_class(obj, name)

  if request.method == 'GET':
    form = make_form(form_class, request, instance=instance_for(form_class, obj), prefix=name)
    return api_response(request, entry=entry, obj=obj, html=_form_html(entry, obj, name, form, request))

  if request.POST.get(MODIFIED_FIELD, '') != _modified(obj):
    return api_response(
      request, status=409, entry=entry, obj=obj,
      error=_("This was changed by someone else since you opened it - reload the page to see the new version."),
      errors={'stale': True},
    )
  # prefix: field names/ids unique per block, so two open forms can't clash.
  # form.request: a form may decide per user (e.g. actions(user)).
  form = make_form(form_class, request, request.POST, instance=instance_for(form_class, obj), prefix=name)
  if not form.is_valid():
    return api_response(
      request, status=400, entry=entry, obj=obj, html=_form_html(entry, obj, name, form, request),
      error=_("Please correct the errors in the form."), errors={'validation': form.errors.get_json_data()},
    )
  changed = form.changed_data
  form.save()   # obj itself, or its related record (instance_for)
  if changed:
    labels = ', '.join(str(form.fields[field].label or field) for field in changed)
    log_change(request, obj, f"Changed {labels} (on the page)")
    message = getattr(form, 'success_message', None)   # e.g. after "deleted"
    messages.success(request, (message() if message else None) or _("Saved."))
  if hasattr(obj, 'date_modified'):
    obj.refresh_from_db(fields=['date_modified'])
  # `modified`: the object's new version - the page puts it in its other
  # block forms for this object, so a second save on the same page isn't
  # mistaken for someone else's change (cmnsd.js edit.js).
  response = {
    'modified': _modified(obj),
    'url': obj.get_absolute_url() if hasattr(obj, 'get_absolute_url') else None,
  }
  if not visible_queryset(model_cls, entry, request).filter(pk=obj.pk).exists():
    list_url = getattr(obj, 'get_list_url', None)
    response['redirect'] = list_url() if list_url else '/'
  elif getattr(form_class, 'reload_page', False) and changed:
    response['reload'] = True
  else:
    response['html'] = block_html(entry, obj, name, request)
  return api_response(request, entry=entry, obj=obj, **response)
