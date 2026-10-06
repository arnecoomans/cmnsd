"""
Static files with their content in their name, for production:

  STORAGES = {..., 'staticfiles': {'BACKEND': 'cmnsd.storage.ManifestStaticFilesStorage'}}

`collectstatic` stores each file as e.g. cmnsd.js/viewer.3f2a1c9e0b4d.js and
{% static %} links to that name - a changed file gets a new name, so no
browser keeps running an old copy (an unchanged one can be cached for
good). cmnsd.js is a set of ES modules that import each other
(`import { request } from './api.js'`): those imports are rewritten to the
hashed names too (support_js_module_import_aggregation), else a module
would still load its neighbours under their plain, cacheable names.

While developing (DEBUG), {% static %} keeps the plain names and runserver
serves the files as they are. Tests use the plain storage: there's no
collected manifest to look names up in (settings).
"""

import logging

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage as DjangoManifestStaticFilesStorage

logger = logging.getLogger(__name__)


class ManifestStaticFilesStorage(DjangoManifestStaticFilesStorage):
  support_js_module_import_aggregation = True

  def hashed_name(self, name, content=None, filename=None):
    """As Django's, but a reference to a file that doesn't exist - in a
    vendored package, e.g. a package's own stylesheet copied along with
    its images, pointing at fonts that weren't - stays as it is (it was
    broken already) instead of stopping collectstatic. Logged. A template's
    {% static %} of a missing file still fails: that lookup goes through
    the manifest (manifest_strict)."""
    try:
      return super().hashed_name(name, content, filename)
    except ValueError as error:
      if content is None and not self.exists(self.clean_name(name).split('?', 1)[0].split('#', 1)[0]):
        logger.warning("Static file reference not found, left unhashed: %s (%s)", name, error)
        return name
      raise
