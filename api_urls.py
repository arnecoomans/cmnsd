from django.urls import path

from cmnsd.views.api import (
  object_child, object_child_delete, object_children, object_create, object_endpoint, object_fields, object_form,
  object_list, object_suggest,
)

app_name = 'cmnsd_api'

urlpatterns = [
  path('<str:model>/', object_list, name='object_list'),
  # Suggestions for a recurring free-text field (object_suggest) - before
  # the object URLs: 'suggest' is never a token (tokens are 10 characters).
  path('<str:model>/suggest/<str:name>/', object_suggest, name='object_suggest'),
  # A new object from a small form, in a dialog (object_create, cmnsd.js
  # dialog.js) - before the object URLs: 'new' is never a token.
  path('<str:model>/new/', object_create, name='object_create'),
  # 'identifier', not 'token' - in DEBUG it may be interpreted as a raw pk
  # instead (see object_fields()'s lookup), a manual-testing convenience
  # only. Real code (this site's own templates/JS) always builds these
  # URLs from the actual token, never a pk - nothing here makes a pk-based
  # URL reversible or otherwise reachable from application code.
  path('<str:model>/<str:identifier>/', object_fields, name='object_fields'),
  # GET: read a field (object_fields). POST: call an @api_action
  # (object_action) - one URL shape, split by method.
  path('<str:model>/<str:identifier>/<str:field>/', object_endpoint, name='object_field'),
  # Edit mode: one block of fields - GET its form, POST to save it
  # (object_form, cmnsd.js edit.js).
  path('<str:model>/<str:identifier>/form/<str:name>/', object_form, name='object_form'),
  # Edit mode: child records of an object (object_children) - add, edit, remove.
  path('<str:model>/<str:identifier>/children/<str:relation>/', object_children, name='object_children'),
  path('<str:model>/<str:identifier>/children/<str:relation>/<int:child_id>/', object_child, name='object_child'),
  path('<str:model>/<str:identifier>/children/<str:relation>/<int:child_id>/delete/', object_child_delete, name='object_child_delete'),
]
