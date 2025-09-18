from django.urls import path

from . import views

app_name = 'cmnsd'

urlpatterns = [
  path('<str:model>/', views.JsonDispatch.as_view(), name='dispatch'),
  path('<str:model>/<int:object_id>/', views.JsonDispatch.as_view(), name='dispatch_object_by_id'),
  path('<str:model>/<int:object_id>-<str:object_slug>/', views.JsonDispatch.as_view(), name='dispatch_object_by_id_and_slug'),
  path('<str:model>/<int:object_id>/<str:field>/', views.JsonDispatch.as_view(), name='dispatch_field_of_object_by_slug'),
  path('<str:model>/<int:object_id>-<str:object_slug>/<str:field>/', views.JsonDispatch.as_view(), name='dispatch_field_of_object_by_id_and_slug'),
]