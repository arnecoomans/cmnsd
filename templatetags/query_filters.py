import json
import re
from django import template
from django.core.serializers.json import DjangoJSONEncoder
from django.http import QueryDict

register = template.Library()

_VALUE_SPLIT_RE = re.compile(r'__and__|,')


def _querystring(query_params, empty=''):
  return f"?{query_params.urlencode()}" if query_params else empty


@register.filter
def tojson(value):
    # Not marked safe on purpose: Django's own autoescaping HTML-entity-encodes
    # the quotes/angle brackets, which is what keeps this safe to interpolate
    # into an HTML attribute (e.g. data-items="{{ items|tojson }}").
    return json.dumps(value, cls=DjangoJSONEncoder)

''' Update Query Params 
    Allows to add and remove qyery parameters from the current URL
    keeping the other parameters intact.

    Use in templates like this:
    {% load query_filters %}
    <a href="{% url 'baseurl' %}{% update_query_params request add='tag1' to='tags' %}">Add tag1</a>
    <a href="{% url 'baseurl' %}{% update_query_params request remove='tag1' to='tags' %}">Remove tag1</a>
    <a href="{% url 'baseurl' %}{% update_query_params request replace='newvalue' to='category' %}">Replace category with newvalue</a>
'''

@register.simple_tag
def update_query_params(request, add=None, remove=None, to=None, replace=None, clear=None):
    query_params = request.GET.copy()

    # Return the current query parameters if no modifications are specified
    if not add and not remove and not replace and not clear:
        return _querystring(query_params)
    # Ensure the 'to' argument is provided (the parameter to modify)
    if not to:
      raise ValueError("You must provide a 'to' argument specifying which query parameter to modify.")

    # Handle clearing a parameter entirely (remove the key regardless of its current value)
    if clear:
      query_params.pop(to, None)
      return _querystring(query_params, empty='?')

    # Handle adding a value to the specified parameter (e.g., 'tags' or 'category')
    if add:
      existing_values = [v for v in _VALUE_SPLIT_RE.split(query_params.get(to, '')) if v]
      if add not in existing_values:
        existing_values.append(str(add))
      query_params[to] = '__and__'.join(existing_values)

    # Handle removing a value from the specified parameter
    if remove:
      existing_values = [v for v in _VALUE_SPLIT_RE.split(query_params.get(to, '')) if v]
      if not isinstance(remove, list):
        remove = [remove]
      for r in remove:
        if r in existing_values:
          existing_values.remove(r)
      if existing_values:
        query_params[to] = '__and__'.join(existing_values)
      else:
        query_params.pop(to, None)

    # Handle replacing the value of the specified parameter
    if replace:
      query_params[to] = replace

    return _querystring(query_params, empty='?')

@register.simple_tag
def copy_query_params(request, prepend=''):
    """Return the current query string, optionally with every key prefixed
    (e.g. prepend='sub_' turns ?tag=a into ?sub_tag=a) - the caller supplies
    any separator as part of prepend itself."""
    query_params = request.GET.copy()
    if prepend:
        prefixed = QueryDict(mutable=True)
        for key, values in request.GET.lists():
            for value in values:
                prefixed.appendlist(prepend + key, value)
        query_params = prefixed
    return _querystring(query_params)