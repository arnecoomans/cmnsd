"""
Admin mixins for CMNSD model mixins. Each one composes via Django's
override-friendly get_*() hook methods (get_list_filter, get_readonly_fields,
get_list_display) with a super() call first, NOT plain class attributes
(list_filter = (...), readonly_fields = (...)) - plain attributes don't merge
across multiple inheritance the way model fields do, so mixing several admin
mixins that each set the same attribute directly would silently drop all but
the last one in the MRO. The get_*() methods are Django's own escape hatch
for exactly this composition problem.

Not every CMNSD model mixin has (or needs) an admin counterpart:
- TokenMixin's token is already editable=False, so Django excludes it from
  the admin form automatically - nothing to add.
- SearchableMixin has no fields at all.
"""
from .OwnershipAdminMixin import OwnershipAdminMixin
from .StatusAdminMixin import StatusAdminMixin
from .VisibilityAdminMixin import VisibilityAdminMixin
from .TimestampAdminMixin import TimestampAdminMixin
from .HierarchyAdminMixin import HierarchyAdminMixin
from .TranslationAliasAdminMixin import TranslationAliasAdminMixin

__all__ = [
  'OwnershipAdminMixin',
  'StatusAdminMixin',
  'VisibilityAdminMixin',
  'TimestampAdminMixin',
  'HierarchyAdminMixin',
  'TranslationAliasAdminMixin',
]
