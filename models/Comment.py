# cmnsd/models/comment.py
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from cmnsd.models.BaseModel import BaseModel
from cmnsd.models.VisibilityModel import VisibilityModel


class BaseComment(BaseModel, VisibilityModel):
  """
  Reusable comment model that supports attaching comments to *any* model
  through a GenericForeignKey.

  Features:
  - inherits BaseModel (token, status, timestamps, user)
  - inherits VisibilityModel (visibility field and filtering)
  - content_object points to any Django model
  - safe to use with cmnsd AJAX dispatch
  - no migrations needed in project apps

  To enable creation via cmnsd AJAX dispatch, override content_type_map in
  the concrete subclass:

    content_type_map = {'location': 'locations.location'}

  The client sends content_for=<key> and content_token=<token> (or content_id=<id>).
  The dispatch resolves the ContentType and object_id server-side — the client
  never touches raw ContentType IDs.
  """

  # Map of allowed content types for creation via AJAX dispatch.
  # Key   = string sent by the client (e.g. 'location')
  # Value = Django app_label.model_name string (e.g. 'locations.location')
  # Override in concrete subclass to enable dispatch-based creation.
  content_type_map = {}

  # Generic relation: content_object = any Django model instance
  content_type = models.ForeignKey(
    ContentType,
    on_delete=models.CASCADE,
    related_name="comments",
  )
  object_id = models.PositiveBigIntegerField()
  content_object = GenericForeignKey("content_type", "object_id")

  text = models.TextField(
    verbose_name=_("comment text"),
    help_text=_("markdown supported".capitalize()),
  )

  # Optional title/subject
  title = models.CharField(
    max_length=255,
    blank=True,
    default="",
    verbose_name=_("title"),
  )

  class Meta:
    ordering = ["-date_created"]
    abstract = True

  def save(self, *args, **kwargs):
    # Do not save a comment with no content
    if not self.text.strip():
      raise ValueError("Cannot save a comment with empty text.")
    return super().save(*args, **kwargs)

  def get_title(self):
    """
    Return the title of the comment, or a truncated preview of the text.
    """
    if self.title:
      return self.title
    preview = self.text.strip()[:60]
    return _("Comment: {preview}…").format(preview=preview) if len(self.text.strip()) > 60 else preview

  def __str__(self):
    return self.get_title()

  # ----------------------------
  # AJAX helpers
  # ----------------------------
  @property
  def ajax_fields(self):
    """
    Which fields may be updated by cmnsd AJAX?
    """
    return ["text", "title", "visibility"]

  @property
  def disallow_access_fields(self):
    """
    Prevent AJAX from touching internal keys.
    """
    return ["content_type", "object_id", "content_object"]

  # Optional: make comments searchable
  @classmethod
  def get_searchable_fields(cls):
    return super().get_searchable_fields() + ["text", "title", "user__username"]
