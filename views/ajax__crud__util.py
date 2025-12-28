from django.conf import settings
from django.utils.translation import gettext_lazy as _

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