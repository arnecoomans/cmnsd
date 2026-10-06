from django.http import Http404
from django.shortcuts import render
from django.utils import translation

from cmnsd.models import Page
from cmnsd.ui.languages import default_language


def page_detail(request, slug):
  """pages/<slug>/ - the page in the visitor's language (the active one:
  a user's preference, or what the locale middleware detected), else in
  the site's default language; 404 when neither is there.

  Public route - always the published version, regardless of who's
  looking. StatusMixin.filter_status() assumes OwnershipMixin's `user`
  field for its "own concept" branch, which Page deliberately doesn't
  have (these are admin-managed pages, not user content) - staff preview
  drafts via /admin/, not this URL."""
  pages = Page.objects.filter(slug=slug, status=Page.Status.PUBLISHED)
  active = (translation.get_language() or default_language()).split('-')[0]
  page = pages.filter(language=active).first() or pages.filter(language=default_language()).first()
  if page is None:
    raise Http404("No such page.")
  return render(request, 'pages/page_detail.html', {'page': page})
