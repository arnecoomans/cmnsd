from django.shortcuts import get_object_or_404, render

from cmnsd.models import Page


def page_detail(request, slug):
  # Public route - always the published version, regardless of who's
  # looking. StatusMixin.filter_status() assumes OwnershipMixin's `user`
  # field for its "own concept" branch, which Page deliberately doesn't
  # have (these are admin-managed pages, not user content) - staff preview
  # drafts via /admin/, not this URL.
  page = get_object_or_404(Page, slug=slug, status=Page.Status.PUBLISHED)
  return render(request, 'pages/page_detail.html', {'page': page})
