# cmnsd/models/comment.py
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from cmnsd.models.cmnsd_basemodel import BaseModel


class BaseComment(BaseModel):
  """
  Reusable comment model that supports attaching comments to *any* model
  through a GenericForeignKey.

  Features:
  - inherits BaseModel (token, status, timestamps, user)
  - content_object points to any Django model
  - safe to use with cmnsd AJAX dispatch
  - no migrations needed in project apps
  """

  # Generic relation: content_object = any Django model instance
  content_type = models.ForeignKey(
    ContentType,
    on_delete=models.CASCADE,
    related_name="comments",
  )
  object_id = models.PositiveIntegerField()
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
    Return the title of the comment, or a default if none is set.
    """
    if self.title:
      return self.title
    return _("Comment #{pk} on {object}").format(pk=self.pk, object=self.content_object)

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

  def disallow_access_fields(self):
    """
    Prevent AJAX from touching internal keys.
    """
    return ["content_type", "object_id", "content_object"]

  # Optional: make comments searchable
  @classmethod
  def get_searchable_fields(cls):
    return ["text", "title", "user__username"]