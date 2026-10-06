from django.contrib import admin

from cmnsd.admin.mixins import TimestampAdminMixin, StatusAdminMixin
from cmnsd.models import Page


@admin.register(Page)
class PageAdmin(TimestampAdminMixin, StatusAdminMixin, admin.ModelAdmin):
  list_display = ('title', 'slug', 'language', 'status')
  list_filter = ('language', 'status')
  search_fields = ('title', 'slug', 'body')
  # A translation keeps its original's slug (one address per page): type it
  # over what this fills in from the translated title.
  prepopulated_fields = {'slug': ('title',)}
  actions = [
    'mark_status_c', 'mark_status_p', 'mark_status_r', 'mark_status_x',
  ]
