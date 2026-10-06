import json


def request_data(request):
  """The data a POST carries, as a dict: a JSON body (what cmnsd.js
  api.js sends), or the form fields of a plain form post. ValueError for
  a malformed body - JSON that doesn't parse (json.JSONDecodeError is a
  ValueError) or isn't an object; the caller answers 400."""
  if request.content_type == 'application/json':
    data = json.loads(request.body or b'{}')
    if not isinstance(data, dict):
      raise ValueError("Expected a JSON object.")
    return data
  return request.POST.dict()
