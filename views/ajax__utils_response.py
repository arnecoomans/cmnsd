from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.context_processors import PermWrapper
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.template.exceptions import TemplateDoesNotExist
from django.db.models.query import QuerySet
from django.db import models
# from django.template import RequestContext

import traceback
import json


class ResponseMixin:
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
      "messages": [self.__render_message(message) for message in self._get_messages()],
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
        "object": str(self.obj) if self.obj and self.obj.is_found() else None,
        "fields": str(self.obj.fields) if self.obj and self.obj.is_found() else None,
        "mode": str(self.modes) if hasattr(self, 'modes') else False,
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
          # "request": self.request,
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
    try:
      return JsonResponse(response_data, status=self.status)
    except TypeError as e:
      if getattr(settings, "DEBUG", False):
        traceback.print_exc()
      staff_message = ': ' + str(e) if getattr(settings, 'DEBUG', False) or self.request.user.is_superuser else ''
      self._add_message(_("error when encoding response to JSON{}").format(staff_message).capitalize(), "error")
      self.status = 500
      response_data["status"] = self.status
      response_data["messages"].append(self.__render_message(self._get_messages()[-1]))
      return JsonResponse(str(response_data), safe=False, status=self.status)
    except Exception as e:
      self._add_message(_("unexpected error when encoding response to JSON: {}").format(str(e)).capitalize(), "error")
      self.status = 500
      response_data["status"] = self.status
      response_data["messages"].append(self.__render_message(self._get_messages()[-1]))
      return JsonResponse(str(response_data), status=self.status)
    
  def render(self, field=None, template_names=[], format='html', context={}):
    ''' In-function configuration '''
    remove_newlines = getattr(settings, 'AJAX_RENDER_REMOVE_NEWLINES', False)
    ''' Add request and permissions to context '''
    context = context | {
      'ajax': getattr(self, 'modes', {'editable': False}),
      'query': self.get_value_from_request(getattr(settings, 'SEARCH_QUERY_CHARACTER', 'q'), silent=True),
    }
    ''' Render attribute via template if available '''
    rendered_field = ''
    if getattr(settings, 'DEBUG', False) and self.request.user.is_staff:
      print(template_names)
    for template in template_names:
      try:
        rendered_field = render_to_string(template, context=context, request=self.request)
        if getattr(settings, 'DEBUG', False) and self.request.user.is_staff:
          print(f"Rendered template: {template}")
      except TemplateDoesNotExist:
        continue
      except Exception as e:
        if getattr(settings, 'DEBUG', False) and self.request.user.is_staff:
          self._add_message(_("error rendering template '{}': {}").format(template, str(e)).capitalize(), "error")
        pass
      try:
        if format == 'json':
          rendered_field = json.loads(rendered_field)
        if remove_newlines and isinstance(rendered_field, str):
          rendered_field = rendered_field.replace('\n', '').replace('\r', '').replace('\t', '')
          while '  ' in rendered_field:
            rendered_field = rendered_field.replace('  ', ' ')
        return rendered_field
      except json.JSONDecodeError as e:
        if getattr(settings, 'DEBUG', False) and self.request.user.is_staff:
          print(f"Error decoding JSON from rendered template '{template}':")
          print(rendered_field)
          print(traceback.format_exc())
        if self.request.user.is_staff:
          self._add_message(_("error decoding JSON from rendered template '{}': {}").format(template, str(e)).capitalize(), "error")
        return ""
      except ValueError as e:
        return ""
    ''' No template found, return string value of field '''
    staff_message = ''
    if self.request.user.is_staff:
      staff_message = '. ' + "\n" + _('searched for templates: {}').capitalize().format(', '.join(template_names))
    self._add_message(_("{} template for '{}:{}' not found in field/ when rendering field").format(format, self.model.name, field).capitalize() + staff_message, "debug")
    if not field or not hasattr(self.obj, field):
      return ''
    return str(getattr(self.obj, field).value())

  def render_field(self, field, format='html', context={}):
    if getattr(settings, 'DEBUG', False) and self.request.user.is_staff:
      print("Rendering field:", field)
    # Try to get field value from object or obj attribute
    try:
      value = getattr(self.obj, field, None)
    except AttributeError:
      try:
        value = getattr(self.obj.obj, field, None)
      except AttributeError:
        raise ValueError(_("field '{}' is not found in {} '{}'".format(field, self.model.name, self.obj)).capitalize())
      except Exception as e:
        raise ValueError(_("unexpected error retrieving field '{}' from {} '{}': {}".format(field, self.model.name, self.obj, str(e))).capitalize())
    except Exception as e:
      raise ValueError(_("unexpected error retrieving field '{}' from {} '{}': {}".format(field, self.model.name, self.obj, str(e))).capitalize())
    if hasattr(value, 'value') and callable(value.value):
      value = value.value()
    ''' Build template names to try to render '''
    template_names = [
      f'object/{ self.model.name.lower() }_{ field }.{ format }',
    ]
    if self.model.has_function(field):
      template_names += [
        f'function/{ self.model.name.lower() }/{ field }.{ format }',
        f'function/{ self.model.name.lower() }_{ field }.{ format }',
        f'function/{ field }.{ format }',
      ]
    template_names += [
      f'field/{ self.model.name.lower() }/{ field }.{ format }',
      f'field/{ self.model.name.lower() }_{ field }.{ format }',
      f'field/{ field }.{ format }',
    ]
    # Prepend template list with model-specific field template if available
    try:
      if hasattr(getattr(self.obj, field).related_model(), 'ajax_template_name') and getattr(self.obj, field).related_model().ajax_template_name:
        template_names.insert(0, f'field/{ getattr(self.obj, field).related_model().ajax_template_name }.{ format }')
    except Exception:
      pass
    # Add date-specific template if field is a DateField or DateTimeField
    if self.model.has_field(field):
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
  def render_object(self, obj, format='html', context={}):
    ''' Alias for render_obj '''
    return self.render_obj(obj, format=format, context=context)
  

  def render_model(self, model, format='html', context={}):
    ''' Ignore empty model '''
    if not model or not model.model:
      return ''
    model_name = model.model._meta.verbose_name_plural
    ''' Build template names to try to render 
        Check for:
        - model/<plural model name>/list.format
        - model/<plural model name>_list.format
        - model/<plural model name>.format
        - model/<model name>/list.format
        - model/<model name>_list.format
        - model/<model name>.format
    '''  
    template_names = [
      f'model/{ model_name.lower() }/list.{ format }',
      f'model/{ model_name.lower() }_list.{ format }',
      f'model/{ model_name.lower() }.{ format }',
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
    self._add_message(_("Message template not found when rendering message").capitalize(), "debug")
    return str(message)
  
  def _add_message(self, message = '', level='info'):
    if not hasattr(self, 'messages'):
      if getattr(settings, 'DEBUG', False):
        print("Messages object not found in FilterMixin when trying to add message: {}".format(message))
      return
    self._add_message(message, level)
  def _get_messages(self):
    if not hasattr(self, 'messages'):
      if getattr(settings, 'DEBUG', False):
        print("Messages object not found in FilterMixin when trying to get messages")
      return []
    return self.messages.get()