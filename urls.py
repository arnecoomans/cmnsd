from django.urls import path

from . import views

app_name = 'cmnsd'

urlpatterns = [
  # List model objects
  path('<str:model>/', views.AjaxDispatch.as_view(), name='dispatch'),
  # Show object details
  path('<str:model>/<int:object_id>-<str:object_slug>/', views.AjaxDispatch.as_view(), name='dispatch_object_by_id_and_slug'),
  # Show objects field details
  path('<str:model>/<int:object_id>-<str:object_slug>/<str:field>/', views.AjaxDispatch.as_view(), name='dispatch_field_of_object_by_id_and_slug'),
]