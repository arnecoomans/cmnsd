from django.urls import path

from cmnsd.views.pages.page_detail import page_detail

app_name = 'cmnsd'

urlpatterns = [
  path('<slug:slug>/', page_detail, name='page'),
]
