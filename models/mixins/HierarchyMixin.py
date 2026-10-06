from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class HierarchyMixin(models.Model):
  """
  Self-referential parent hierarchy, plus compound-name auto-splitting:
  saving name="Media: Book" (or "Nederlandsch-Indië: Java: Batavia") with no
  parent set get_or_creates each ancestor level and leaves self as just the
  leaf name under the resolved parent chain. An explicitly-set parent always
  wins over the string heuristic - the split only runs when parent is unset.

  Assumes the composing model has a plain CharField `name`. If it also has
  OwnershipMixin's `user`, an auto-created ancestor inherits it (user has no
  field default by design); otherwise no 'user' default is passed.
  """
  parent = models.ForeignKey("self", on_delete=models.PROTECT, related_name='children', null=True, blank=True)

  class Meta:
    abstract = True

  def clean(self):
    # If name still contains the compounder here, either parent was already
    # set explicitly (so _split_compounded_name() deliberately left it
    # alone) or the split couldn't fully resolve it (e.g. "Media: " with
    # nothing after the compounder) - either way, a name containing the
    # separator is not a valid leaf name.
    compounder = getattr(settings, 'CMNSD_PARENT_COMPOUNDER', ': ')
    if self.name and compounder in self.name:
      raise ValidationError({
        'name': _("Name must not contain the parent/child separator '%(compounder)s' - use the parent field instead.") % {'compounder': compounder},
      })
    # No loops: not its own parent, nor below one of its own descendants.
    node = self.parent
    while node is not None:
      if self.pk is not None and node.pk == self.pk:
        raise ValidationError({'parent': _("This would make it its own ancestor.")})
      node = node.parent

  def _split_compounded_name(self):
    if self.parent:
      return
    compounder = getattr(settings, 'CMNSD_PARENT_COMPOUNDER', ': ')
    while self.name and compounder in self.name:
      parent_name, _sep, remainder = self.name.partition(compounder)
      parent_name, remainder = parent_name.strip(), remainder.strip()
      if not (parent_name and remainder):
        break
      defaults = {'user': self.user} if hasattr(self, 'user') else {}
      parent, _created = self.__class__.objects.get_or_create(
        name=parent_name, parent=self.parent, defaults=defaults,
      )
      self.parent = parent
      self.name = remainder

  def display_name(self, compounder=None) -> str:
    if compounder is None:
      compounder = getattr(settings, 'CMNSD_PARENT_COMPOUNDER', ': ')
    return compounder.join(node.name for node in self.ancestors())

  def ancestors(self):
    """Root-to-self chain, e.g. [Nederlandsch-Indië, Java, Batavia] - for
    tagging/displaying at any level of the hierarchy, not just the leaf."""
    chain, seen = [], set()
    node = self
    # Stops at a loop (a row saved around clean(), e.g. by an import): a
    # broken hierarchy shows wrong, it doesn't crash every page it's on.
    while node and node.pk not in seen:
      if node.pk is not None:
        seen.add(node.pk)
      chain.append(node)
      node = node.parent
    return list(reversed(chain))
