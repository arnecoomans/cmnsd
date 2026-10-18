from cmnsd.models.Mention import _ADDED, mention_notices


class MentionNoticeMiddleware:
  """Collects the mentions added while handling a request (cmnsd.models.
  Mention sync_mentions) and warns about those fewer may see than the text
  they're in (mention_notices) - an API response tells them itself; for any
  other, they're queued for the next page. After MessageMiddleware."""

  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    token = _ADDED.set([])
    try:
      response = self.get_response(request)
      mention_notices(request)
    finally:
      _ADDED.reset(token)
    return response
