from django.urls import path

from . import views

app_name = 'cmnsd'

urlpatterns = [
  path('json/<str:model>/', views.JsonDispatch.as_view(), name='dispatch'),

]