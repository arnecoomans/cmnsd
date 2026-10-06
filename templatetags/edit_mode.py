from django import template
from django.urls import reverse

from cmnsd.edit.mode import can_edit as _can_edit

register = template.Library()


@register.filter
def can_edit(obj, request):
  """{% if edit_mode and content|can_edit:request %} - whether this viewer
  may change this object (cmnsd/edit/mode.py: the object's can_edit(user),
  else the model's change permission). Combine with `edit_mode`: the
  filter says "may", the switch says "wants to now"."""
  return _can_edit(obj, getattr(request, 'user', None))


@register.inclusion_tag('cmnsd/edit/choices.html', takes_context=True)
def edit_choices(context, obj, block, style='buttons'):
  """{% edit_choices content 'visibility' %} - a choice block's form: the
  block's one field (its form in the model's api_edit_forms, form class
  `choice = True`) as a row of buttons that save on click, or with
  style='select' a dropdown that saves on change (a longer list). Values
  in the form class's `confirm` ask first; `choice_hints` ({value: text})
  explain a choice (the button's tooltip), so everyone picks alike.
  Posted like any block form (cmnsd object_form, cmnsd.js edit.js)."""
  from cmnsd.api.registry import API_REGISTRY
  from cmnsd.views.api.object_form import MODIFIED_FIELD, _form_class, _modified, instance_for
  form_class = _form_class(obj, block)
  form = form_class(instance=instance_for(form_class, obj), prefix=block)
  field = next(iter(form))
  model = API_REGISTRY[type(obj)]['name']
  current = '' if field.value() is None else str(field.value())
  confirm = getattr(form_class, 'confirm', {}) or {}
  hints = getattr(form_class, 'choice_hints', {}) or {}
  actions = getattr(form, 'actions', None)
  if actions:
    # An action block: what can be done next, for this user ("Publish",
    # "Revoke") - the current value is shown as text, not as a button.
    user = getattr(context.get('request'), 'user', None)
    # (value, label) or (value, label, 'before'): a step back is shown
    # before the current value, the rest after it - it reads as a flow:
    # (Back to draft) Published (Delete).
    choices = [
      {'value': str(action[0]), 'label': action[1], 'current': False, 'confirm': confirm.get(action[0], ''),
       'before': len(action) > 2 and action[2] == 'before'}
      for action in actions(user)
    ]
    current_label = dict(field.field.choices).get(field.value(), current)
  else:
    current_label = ''
    choices = [
      {'value': str(value), 'label': label, 'current': str(value) == current, 'confirm': confirm.get(value, ''), 'hint': hints.get(value, '')}
      for value, label in field.field.choices if str(value) != ''
    ]
    if style == 'select' and not field.field.required:
      # A field that may be empty: "—" for not set - otherwise the browser
      # shows the first real choice as if it were the value.
      choices.insert(0, {'value': '', 'label': '—', 'current': current == '', 'confirm': ''})
  return {
    'url': reverse('cmnsd_api:object_form', args=[model, obj.token, block]),
    'field': field, 'choices': choices, 'style': style, 'current_label': current_label,
    'modified': _modified(obj), 'modified_field': MODIFIED_FIELD,
  }


# --- child records (cmnsd/views/api/object_children.py) ----------------------

@register.simple_tag(takes_context=True)
def child_permissions(context, obj, relation):
  """{% child_permissions obj 'transcripts' as perms_child %} - {add,
  change, delete} for this viewer: the child model's own permissions."""
  from cmnsd.views.api.object_children import child_permissions as permissions
  return permissions(getattr(context.get('request'), 'user', None), obj, relation)


@register.simple_tag
def child_urls(model, obj, relation, child=None):
  """{% child_urls 'content' obj 'transcripts' child as urls %} - {edit,
  delete} for a child, {add} without one."""
  from cmnsd.views.api.object_children import child_urls as urls
  return urls(model, obj, relation, child)


@register.simple_tag
def child_add_label(obj, relation):
  """The "+ add" text: the relation's add_label, else "Add <verbose name>"."""
  from django.utils.text import capfirst
  from django.utils.translation import gettext as _
  from cmnsd.views.api.object_children import child_config, child_manager
  label = child_config(obj, relation).get('add_label')
  return capfirst(label or _("add %(name)s") % {'name': child_manager(obj, relation).model._meta.verbose_name})


@register.filter
def tokens(objects, extra=None):
  """{{ tags|tokens }} -> 'aB3..,cD4..' - the tokens of a list of objects,
  for a picker's exclude (cmnsd/edit/link_picker.html: don't offer what's
  linked already). {{ parents|tokens:person }} adds that object's token
  too (e.g. the person themselves)."""
  found = [obj.token for obj in objects or ()]
  if extra is not None:
    found.append(extra.token)
  return ','.join(found)
