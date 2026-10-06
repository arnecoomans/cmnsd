"""
Changes made on the site's pages (edit mode) are written to Django's admin
log (LogEntry), so they show in each object's admin "History" next to
changes made in the admin itself - no model of its own. Full version
history (with undo) is a separate, later decision.
"""

from django.contrib.admin.models import CHANGE, LogEntry


def log_change(request, obj, message):
  """Record `message` (plain text, e.g. "Added part 3: Back cover") as a
  change of `obj` by the request's user."""
  LogEntry.objects.log_actions(
    request.user.pk, [obj], CHANGE, change_message=message, single_object=True,
  )
