from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
import traceback

from .json_utils_meta_class import meta_field
class CrudUtil:
  
  
  def verify_object(self):
    """
    Verify that both a model and an object are set before performing an update.

    This method ensures that the current view or handler has correctly
    initialized its target model (`self.model`) and object (`self.obj`)
    before attempting any database operation. It raises a descriptive
    error if either is missing.

    Returns:
      bool: Always returns ``True`` if both checks pass.

    Raises:
      ValueError: If no model or object is detected for the update process.
    """
    if not self.model:
      raise ValueError(_("no model detected for update").capitalize())
    elif not self.obj:
      raise ValueError(_("no object detected for update").capitalize())
    return True
  
  def get_field(self, sources=None):
    field = False
    # Check if field is supplied in request URL (kwargs)
    if self.obj.fields:
      print(self.obj.fields)
      # Assume first field if multiple fields are supplied
      field = self.obj.fields[0]
      if self.obj.fields.__len__() > 1:
        self.messages.add(_("multiple fields were supplied but only one is supported").capitalize() + ". " + _("using first field '{}'").format(field).capitalize(), 'warning')
    else:
      # Check if field is supplied in request data (POST or JSON)
      fields = self.get_keys_from_request(sources=self.get_sources())
      for f in fields:
        if self.model.is_field(f):
          field = f
          # Only use the first valid field found, assume the rest are value identifiers
          break
    if not field:
      raise ValueError(_("no valid field supplied for update").capitalize())
    return field
  
  # def get_fields(self):
  #   # Get all fields mentioned in payload that can be mapped to the object fields
  #   fields = []
  #   for key in self.get_keys_from_request(sources=self.get_sources()):
  #     if self.model.is_field(key):
  #       try:
  #         fields.append(self.validate_field(key))
  #       except Exception as e:
  #         # Ignore invalid fields
  #         print(e)
  #         pass
  #   if not fields:
  #     raise ValueError(_("no valid fields supplied for update").capitalize())
  #   return fields
  
  # def get_field(self, sources=None):
  #   """
  #   Determine the target model field to be updated or accessed.

  #   This method attempts to detect which field of the current model
  #   (`self.model`) should be used for an operation, based on the
  #   available request context or URL parameters.

  #   The lookup order is as follows:
  #     1. If one or more fields are supplied via the URL (``self.obj.fields``),
  #       use the first field in that list. A warning message is added if
  #       multiple fields were provided.
  #     2. Otherwise, search for the first valid field name found in the request
  #       data (e.g. POST, JSON, or GET), using ``get_keys_from_request()``
  #       combined with the configured input sources from ``get_sources()``.

  #   Args:
  #     sources (list | None): Optional list of data sources to search for
  #       field names. If not provided, defaults to ``self.get_sources()``.

  #   Returns:
  #     str: The name of the detected model field.

  #   Raises:
  #     ValueError: If no valid field name could be determined.

  #   Side Effects:
  #     - Logs a warning message to ``self.messages`` if multiple fields were
  #       provided in the request.
  #     - Prints debug information about detected fields (useful during
  #       development).

  #   Example:
  #     If a request URL provides ``/json/location/111-slug/name/``, this
  #     method will return ``"name"``.
  #   """
  #   field = False

  #   # Check if field is supplied in request URL (kwargs)
  #   if self.obj.fields:
  #     # Assume first field if multiple fields are supplied
  #     field = self.obj.fields[0]
  #     if len(self.obj.fields) > 1:
  #       self.messages.add(
  #         _("multiple fields were supplied but only one is supported").capitalize()
  #         + ". "
  #         + _("using first field '{}'").format(field).capitalize(),
  #         "warning"
  #       )

  #   else:
  #     # Check if field is supplied in request data (POST or JSON)
  #     fields = self.get_keys_from_request(sources=self.get_sources())
  #     for f in fields:
  #       if self.model.is_field(f):
  #         field = f
  #         # Only use the first valid field found, assume the rest are value identifiers
  #         break

  #   if not field:
  #     raise ValueError(_("no valid field supplied for update").capitalize())

  #   return field

  
  def get_sources(self):
    """
    Define the preferred data sources to extract field values or parameters from a request.

    This method specifies which request sources are considered safe and relevant
    when retrieving data during internal operations such as model updates or field
    lookups. It helps differentiate between **request parameters** (e.g., identifying
    which object to modify) and **payload data** (e.g., which fields to change).

    The default behavior prioritizes structured input sources (`JSON` and `POST`)
    to ensure consistent and secure data extraction. When Django's debug mode is
    active (`settings.DEBUG = True`), `GET` parameters are also allowed to assist
    with development and manual testing.

    Returns:
      list[str]: A list of allowed request data sources, typically
        ``['json', 'POST']`` in production or ``['json', 'POST', 'GET']`` in
        debug mode.

    Example:
      ```python
      # In production:
      self.get_sources()
      # → ['json', 'POST']

      # In development (DEBUG=True):
      self.get_sources()
      # → ['json', 'POST', 'GET']
      ```

    Notes:
      - This function is used internally by data access helpers such as
        ``get_value_from_request()`` and ``get_field()``.
      - The returned order indicates **priority** — JSON payloads are checked first,
        then form submissions, and finally query parameters (if allowed).
    """
    sources = ['json', 'POST']
    if getattr(settings, 'DEBUG', False):
      sources.append('GET')
    return sources