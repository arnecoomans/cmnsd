from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.context_processors import PermWrapper
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.template.exceptions import TemplateDoesNotExist
from django.db.models.query import QuerySet
from django.db import models

import json


class ResponseUtil:
  def __init__(self):
    self.status = 200
    super().__init__()

  def dispatch(self, request, *args, **kwargs):
    return super().dispatch(request, *args, **kwargs)

  def return_response(self, payload=None, **kwargs):
    """
    Prepare and return a structured JSON response.
    """
    model_name = self.model
    object_name = self.obj if self.model else None
    fields = self.obj.fields if hasattr(self.obj, 'fields') else None
    if 'status' in kwargs:
      self.status = kwargs.pop('status')
    ''' Get model name, object name and attributes '''
    response_data = {
      "status": self.status,
      "messages": [self.__render_message(message) for message in self.messages.get()],
    }
    ''' Add payload to response if present '''
    if payload:
      if isinstance(payload, dict):
        # if payload is a dict, strip all string values and remove empty lines
        payload = {
          key: (
            "\n".join(line for line in value.splitlines() if line.strip()).strip()
            if isinstance(value, str)
            else value
          )
          for key, value in payload.items()
        }
      response_data["payload"] = payload
    ''' When other arguments are passed when calling return_response,
        they will be added to the response as well.
    '''
    for key, value in kwargs.items():
      if key != "payload":
        response_data[key] = value
    ''' Add meta information to response if user is staff '''
    if self.request.user.is_staff:
      response_data["__meta"] = {
        "model": str(self.model.name if self.model else None),
        "object": str(self.obj if self.obj else None),
        "fields": str(self.obj.fields) if self.obj else None,
        "mode": str(self.modes) if hasattr(self, 'modes') else False,
        "payload_size": str(self.__get_payload_size(payload)),
        "debug": settings.DEBUG,
        "request_user": {
          "id": self.request.user.id,
          "username": self.request.user.username,
          "is_staff": self.request.user.is_staff,
          "is_superuser": self.request.user.is_superuser,
        },
        "request": {
          "path": self.request.path,
          "method": self.request.method,
          "handler": self.__class__.__name__,
          "resolver": self.request.resolver_match.url_name,
          # "csrf": "present" if self.csrf_token else "missing",
        },
      }
      # Add url.py configured arguments to debug info
      for kwarg in self.kwargs:
        response_data['__meta']['request']['url_' + kwarg] = self.get_value_from_request(kwarg)
      # Add GET parameters to debug info
      for key, value in self.request.GET.items():
        response_data['__meta']['request']['get_' + key] = value
      # Add POST parameters to debug info
      for key, value in self.request.POST.items():
        response_data['__meta']['request']['post_' + key] = value
    return JsonResponse(response_data)

  def __get_payload_size(self, payload):
    payload_size = 0
    if type(payload) == list:
      payload_size = len(payload)
    elif type(payload) == dict:
      for value in payload.values():
        payload_size += len(value)
    return payload_size

  def render(self, field=None, template_names=[], format='html', context={}):
    ''' In-function configuration '''
    remove_newlines = getattr(settings, 'JSON_RENDER_REMOVE_NEWLINES', False)
    ''' Add request and permissions to context '''
    context = context | {
      'crud_mode': getattr(self, 'modes', {'editable': False}),
      'request': self.request,
      'user': self.request.user,
      'permissions': self.request.user.get_all_permissions(),
    }
    ''' Render attribute via template if available '''
    for template in template_names:
      try:
        rendered_field = render_to_string(template, context)
        if format == 'json':
          rendered_field = json.loads(rendered_field)
        if remove_newlines and isinstance(rendered_field, str):
          rendered_field = rendered_field.replace('\n', '').replace('\r', '').replace('\t', '')
          while '  ' in rendered_field:
            rendered_field = rendered_field.replace('  ', ' ')
        return rendered_field
      except TemplateDoesNotExist:
        pass
    ''' No template found, return string value of field '''
    self.messages.add(_("{} template for '{}:{}' not found in field/ when rendering field").format(format, self.model.name, field).capitalize(), "debug")
    if not field or not hasattr(self.obj, field):
      return ''
    return str(getattr(self.obj, field).value())

  def render_field(self, field, format='html', context={}):
    value = getattr(self.obj, field, None).value()
    ''' Ignore empty field or empty queryset '''
    if  value is None or \
        value is False or \
        len(str(value).strip()) == 0: # or \
        # (isinstance(value, QuerySet) and value.count() == 0):
      return ''
    ''' Build template names to try to render '''
    template_names = [
      f'object/{ self.model.name.lower() }_{ field }.{ format }',
      f'field/{ field }.{ format }',
    ]
    if isinstance(self.model.model._meta.get_field(field), models.DateTimeField) or \
        isinstance(self.model.model._meta.get_field(field), models.DateField):
      template_names.append(f'field/date.{ format }')
    ''' Filter Queryset Results '''
    if isinstance(value, QuerySet) and hasattr(self, 'filter'):
      value = self.filter(value)
    ''' Build rendering context '''
    context = context | {
      'field_name': field,
      'field_value': value,
      field: value,
      'format': format,
      'model': self.model.name,
      'obj': self.obj,
      'q': self.request.GET.get(getattr(settings, 'SEARCH_QUERY_CHARACTER', 'q')),
      self.model.name: self.obj.obj,
    }
    return self.render(field=field, template_names=template_names, format=format, context=context)
  
  def render_obj(self, obj, format='html', context={}):
    ''' Ignore empty object '''
    if not obj or not obj.obj:
      return ''
    ''' Build template names to try to render '''
    template_names = [
      f'object/{ self.model.name.lower() }/detail.{ format }',
      f'object/{ self.model.name.lower() }_detail.{ format }',
      f'object/{ self.model.name.lower() }.{ format }',
    ]
    ''' Build rendering context '''
    context = context | {
      'object': obj.obj,
      'object_name': self.model.name,
      'format': format,
      'model': self.model.name,
      'obj': obj,
      self.model.name: obj.obj,
    }
    return self.render(field=None, template_names=template_names, format=format, context=context)

  def render_model(self, model, format='html', context={}):
    ''' Ignore empty model '''
    if not model or not model.model:
      return ''
    model_name = model.model._meta.verbose_name_plural
    ''' Build template names to try to render '''  
    template_names = [
      # f'model/{ model._meta.verbose_name_plural.lower() }.{ format }',
      f'model/{ model.name.lower() }/list.{ format }',
      f'model/{ model.name.lower() }_list.{ format }',
      f'model/{ model.name.lower() }.{ format }',
    ]
    # Prepend template name with verbose_name_plural if available
    if hasattr(model.model, '_meta'):
      template_names.insert(0, f'model/{ model.model._meta.verbose_name_plural.lower() }.{ format }',)
    ''' Build rendering context '''
    context = context | {
      'model_name': model_name,
      'format': format,
      'model': model.name,
    }
    object_list = model.model.objects.all()
    if hasattr(self, 'filter'):
      object_list = self.filter(object_list)
    context[model_name] = object_list
    return self.render(field=None, template_names=template_names, format=format, context=context)
  
  def __render_message(self, message):
    ''' Render message via template if available '''
    try:
      rendered_message = render_to_string('core/message.html', {'message': message})
      message['rendered'] = rendered_message.replace('\n', '').replace('\r', '').replace('\t', '')
      return message
    except TemplateDoesNotExist:
      pass
    ''' No template found, return string value of message '''
    self.messages.add(_("Message template not found when rendering message").capitalize(), "debug")
    return str(message)