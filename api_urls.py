from django.urls import path

from cmnsd.views.api import object_endpoint, object_fields, object_list

app_name = 'cmnsd_api'

urlpatterns = [
  path('<str:model>/', object_list, name='object_list'),
  # 'identifier', not 'token' - in DEBUG it may be interpreted as a raw pk
  # instead (see object_fields()'s lookup), a manual-testing convenience
  # only. Real code (this site's own templates/JS) always builds these
  # URLs from the actual token, never a pk - nothing here makes a pk-based
  # URL reversible or otherwise reachable from application code.
  path('<str:model>/<str:identifier>/', object_fields, name='object_fields'),
  # GET: read a field (object_fields). POST: call an @api_action
  # (object_action) - one URL shape, split by method.
  path('<str:model>/<str:identifier>/<str:field>/', object_endpoint, name='object_field'),
]
