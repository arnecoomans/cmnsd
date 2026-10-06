from django.contrib import messages
from django.contrib.admin.models import ADDITION, LogEntry
from django.http import Http404
from django.urls import reverse
from django.utils.module_loading import import_string
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from .lookup import resolve_model
from .object_form import _render, make_form
from .response import api_response, api_view


def create_form_class(model_cls):
  """The model's api_create_form - a form class or its dotted path - else
  Http404: nothing can be created through the API unless declared."""
  form_class = getattr(model_cls, 'api_create_form', None)
  if form_class is None:
    raise Http404("This can't be created here.")
  return import_string(form_class) if isinstance(form_class, str) else form_class


def _form_html(entry, form, request):
  context = {
    'form': form, 'model': entry['name'], 'request': request,
    'form_action': reverse('cmnsd_api:object_create', args=[entry['name']]),
  }
  return _render([f"{entry['name']}/forms/new.html", 'cmnsd/edit/create_form.html'], context, request)


def _display(obj, request):
  display = getattr(obj, 'api_display', None)
  return display(request) if display else str(obj)


@api_view
@require_http_methods(['GET', 'POST'])
def object_create(request, model):
  """api/<model>/new/ - create an object from a small form, in a dialog
  (cmnsd.js dialog.js - a picker's "+ new ..." option): the model declares
  api_create_form = 'app.forms.SomeForm' (the same form a page of its own
  may use). GET: the form as `html` (<model>/forms/new.html, else
  cmnsd/edit/create_form.html), its fields prefilled from the query string
  (e.g. ?given_name=Jan - the picker's search). The form gets
  `form.request`, and its prepare() is called when it has one (make_form). POST: valid - saved, owned
  by this user (when the model has a user), logged to the admin history,
  "<name> added." queued; the answer's `created` is {token, name, url} so
  the picker can choose it. Invalid: 400 with the form and its errors.
  Needs the model's add permission. What a new object starts as (status,
  visibility, ...) is the form's business."""
  model_cls, entry = resolve_model(model)
  form_class = create_form_class(model_cls)
  opts = model_cls._meta
  if not (request.user.is_authenticated and request.user.has_perm(f'{opts.app_label}.add_{opts.model_name}')):
    return api_response(request, status=403, entry=entry, error=_("You may not add this."), errors={'permission': True})

  if request.method == 'GET':
    initial = {name: request.GET[name] for name in form_class.base_fields if request.GET.get(name)}
    return api_response(request, entry=entry, html=_form_html(entry, make_form(form_class, request, initial=initial), request))

  form = make_form(form_class, request, request.POST)
  if not form.is_valid():
    return api_response(
      request, status=400, entry=entry, html=_form_html(entry, form, request),
      error=_("Please correct the errors in the form."), errors={'validation': form.errors.get_json_data()},
    )
  obj = form.save(commit=False)
  if any(field.name == 'user' for field in opts.fields) and not getattr(obj, 'user_id', None):
    obj.user = request.user
  obj.save()
  form.save_m2m()
  LogEntry.objects.log_actions(request.user.pk, [obj], ADDITION, change_message="Created on the site", single_object=True)
  name = _display(obj, request)
  messages.success(request, _("%(name)s added.") % {'name': name})
  url = obj.get_absolute_url() if hasattr(obj, 'get_absolute_url') else None
  return api_response(request, entry=entry, obj=obj, created={'token': obj.token, 'name': name, 'url': url})
