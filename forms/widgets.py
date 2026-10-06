from django import forms


class SuggestInput(forms.TextInput):
  """A free-text input that suggests existing values while typing (the
  browser's own <datalist>, filled by cmnsd.js suggest.js from
  cmnsd object_suggest) - choosing one only fills in the text.

    SuggestInput(url='/api/content/suggest/publisher/')
  """
  template_name = 'cmnsd/widgets/suggest.html'

  def __init__(self, url, attrs=None):
    super().__init__({'autocomplete': 'off', **(attrs or {})})
    self.url = url

  def get_context(self, name, value, attrs):
    context = super().get_context(name, value, attrs)
    list_id = f"{context['widget']['attrs'].get('id', name)}-suggestions"
    context['widget']['attrs'].update({'list': list_id, 'data-cmnsd-suggest': self.url})
    context['widget']['list_id'] = list_id
    return context


class PickerInput(forms.HiddenInput):
  """Choose one object by searching for it - for a ModelChoiceField whose
  values are tokens (to_field_name='token'), e.g. a place's parent. Renders
  a picker (cmnsd.js picker.js, results from the model's
  <model>/<model>_picker.html through the API list endpoint) around the
  field's hidden input, with the current choice by name:

    parent = forms.ModelChoiceField(
      Place.objects.all(), to_field_name='token', required=False,
      widget=PickerInput('place', clear_label=_("no parent")),
    )

  Options: `label(obj)` - how the current choice is named (default
  str()); `clear_label` - a button that empties the field (only for an
  optional field); `submit` - submit the form on a choice (an edit block
  saves at once); `exclude` - tokens not to offer (set it per form, e.g.
  the object itself); `create_label` - without an exact match, offer
  "<label> “search”": the name goes in `<field>__new` (new_name()) and the
  form creates the object (with its own permission check). The choice is still validated by the field: the
  picker only offers what the viewer may see, the form decides."""
  template_name = 'cmnsd/widgets/picker.html'

  # Built on a hidden input (the chosen token), but a visible control - not
  # one of the form's hidden_fields(), which templates render without a label.
  @property
  def is_hidden(self):
    return False

  def __init__(self, model, *, label=None, placeholder='', empty_label='—', clear_label='', submit=True, exclude=(), create_label='', attrs=None):
    super().__init__(attrs)
    self.create_label = create_label
    self.model = model
    self.label = label
    self.placeholder = placeholder
    self.empty_label = empty_label
    self.clear_label = clear_label
    self.submit = submit
    self.exclude = exclude

  def _chosen(self, value):
    """The object `value` (a token) names, from the field's own queryset."""
    choices = getattr(self, 'choices', None)
    queryset = getattr(choices, 'queryset', None)
    if not value or queryset is None:
      return None
    key = getattr(choices.field, 'to_field_name', None) or 'pk'
    return queryset.filter(**{key: value}).first()

  def get_context(self, name, value, attrs):
    from cmnsd.api.filtering import search_character
    context = super().get_context(name, value, attrs)
    chosen = self._chosen(context['widget']['value'])
    context['widget'].update({
      'model': self.model,
      'param': search_character(),
      'chosen': chosen,
      'chosen_label': (self.label(chosen) if self.label else str(chosen)) if chosen else '',
      'placeholder': self.placeholder,
      'empty_label': self.empty_label,
      'clear_label': self.clear_label,
      'submit': self.submit,
      'exclude': ','.join(self.exclude),
      'create_label': self.create_label,
      'new_name': f'{name}__new',
    })
    return context

  @staticmethod
  def new_name(form, field):
    """The name typed for a new object in `field`'s picker ("+ create"),
    '' when none."""
    key = f'{form.add_prefix(field)}__new'
    return (form.data.get(key) or '').strip() if form.is_bound else ''
