from django.urls import path

from . import views

app_name = 'cmnsd'

urlpatterns = [
  # List model objects
  path('<str:model>/', views.JsonDispatch.as_view(), name='dispatch'),
  # path('<str:model>/<int:object_id>/', views.JsonDispatch.as_view(), name='dispatch_object_by_id'), # This view allows easy access during development, but should be considered insecure in production
  # Show object details
  path('<str:model>/<int:object_id>-<str:object_slug>/', views.JsonDispatch.as_view(), name='dispatch_object_by_id_and_slug'),
  # path('<str:model>/<int:object_id>/<str:field>/', views.JsonDispatch.as_view(), name='dispatch_field_of_object_by_slug'), # This view allows easy access during development, but should be considered insecure in production
  # Show objects field details
  path('<str:model>/<int:object_id>-<str:object_slug>/<str:field>/', views.JsonDispatch.as_view(), name='dispatch_field_of_object_by_id_and_slug'),
]