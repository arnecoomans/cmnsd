from django.urls import path

from cmnsd.views.ui import edit_mode, section_state, sort_state

# Remembered UI state (cmnsd/ui/state.py): include at e.g. 'ui/' and pass
# the URLs to cmnsd.init() (sectionStateUrl / sortStateUrl) in base.html.
# edit/: the edit-mode switch (cmnsd/edit/mode.py), posted by a form.
app_name = 'cmnsd_ui'

urlpatterns = [
  path('section/', section_state, name='section_state'),
  path('sort/', sort_state, name='sort_state'),
  path('edit/', edit_mode, name='edit_mode'),
]
