from django.contrib import admin

from cmnsd.admin.mixins import TimestampAdminMixin, StatusAdminMixin
from cmnsd.models import Page


@admin.register(Page)
class PageAdmin(TimestampAdminMixin, StatusAdminMixin, admin.ModelAdmin):
  list_display = ('title', 'slug', 'status')
  search_fields = ('title', 'slug', 'body')
  prepopulated_fields = {'slug': ('title',)}
  actions = [
    'mark_status_c', 'mark_status_p', 'mark_status_r', 'mark_status_x',
  ]
