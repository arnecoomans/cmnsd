from django.db.models import Q, QuerySet
from django.db.models.fields import CharField, TextField
from django.db import models
from django.db.models.fields.related import ManyToManyField
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class FilterClass:
  def filter(self, queryset, suppress_search=False):
    model = queryset.model
    search_query_char = getattr(settings, 'SEARCH_QUERY_CHARACTER', 'q')
    search_exclude_char = getattr(settings, 'SEARCH_EXCLUDE_CHARACTER', 'exclude')
    search_fields = self.__get_search_fields(model)
    
    if len(search_fields) > 0 and self.get_value_from_request(search_query_char, default=False, silent=True) and self.get_value_from_request(search_exclude_char, default=False, silent=True):
      # Only apply search filters if there are searchable fields or a search query is provided
      suppress_search = True
    
    try:
      ''' Apply model specific access restrictions '''
      queryset = self.__filter_by_restrict_access(queryset)
      ''' Conditionally filter queryset based on field availablity '''
      if 'status' in [field.name for field in model._meta.get_fields()]:
        queryset = self.filter_status(queryset)
      if 'visibility' in [field.name for field in model._meta.get_fields()]:
        queryset = self.filter_visibility(queryset)
      ''' Check if search should be applied or suppressed '''
      if not suppress_search:
        ''' Field specific filtering '''
        if len(search_fields) > 0:
          queryset = self.search_results(queryset, search_fields)
        ''' Free text search '''
        if self.get_value_from_request(search_query_char, default=False, silent=True):
          queryset = self.filter_freetextsearch(queryset)
        ''' Exclude results based on settings '''
        if self.get_value_from_request(search_exclude_char, default=False, silent=True):
          queryset = self.exclude_results(queryset)
    except Exception as e:
      self.messages.add(str(e), 'error')
      self.status = 400
      return QuerySet(model=model).none()
    ''' Return filtered queryset '''
    return queryset
  
  ''' Security Measure '''
  def __field_is_secure(self, field_name):
    blocked_fields = ['password'] + getattr(settings, 'SEARCH_BLOCKED_FIELDS', [])
    if field_name in blocked_fields:
        self.messages.add(_("field '{}' is not allowed for searching due to security reasons.").format(field_name).capitalize(), "error")
        return False
    if field_name.startswith('_'):
        self.messages.add(_("field '{}' is not allowed for searching due to security reasons.").format(field_name).capitalize(), "error")
        return False
    return True
  
  ''' Restrict Access to objects based on model RESTRICT_READ_ACCESS attribute '''
  def __filter_by_restrict_access(self, queryset):
    model = queryset.model
    if hasattr(model, 'RESTRICT_READ_ACCESS'):
      if model.RESTRICT_READ_ACCESS == 'user':
        if self.request.user.is_authenticated:
          queryset = queryset.filter(user=self.request.user)
        else:
          self.messages.add(_("you must be logged in to view these items").capitalize(), 'error')
          self.status = 403
          return QuerySet(model=model).none()
    return queryset
  
  ''' Get Searchable Fields from request kwargs 
      Loop through request GET and POST parameters and check if they are fields in the model.
      If they are a field, add them to the list of search fields.
  '''
  def __get_search_fields(self, model):
    request_fields = self.__get_searched_fields_from_request()
    model_fields = [field.name for field in model._meta.get_fields()]
    query_fields = []
    for field in request_fields:
      if field.split('__')[0] in model_fields:
        query_fields.append(field)
    return query_fields
  
  """ Get all fields from request GET and POST parameters 
      Return a list of all fields in the request GET and POST parameters."""
  def __get_searched_fields_from_request(self):
    search_fields = []
    for key in self.request.GET.keys():
      if key:
        search_fields.append(key)
    for key in self.request.POST.keys():
      if key:
        search_fields.append(key)
    for field in ['csrfmiddlewaretoken']:
      if field in search_fields:
        search_fields.remove(field)
    for field in search_fields:
      if self.get_value_from_request(field, silent=True) in [None, '']:
        search_fields.remove(field)
    return search_fields
  
  ''' Filter by object status '''
  def filter_status(self, queryset):
    return queryset.filter(status='p')
  
  ''' Filter by object visibility '''
  def filter_visibility(self, queryset):
    ''' Add private objects for current user to queryset '''
    if self.request.user.is_authenticated:
      ''' Show public and community, family if family is configured, and private if owner '''
      queryset =  queryset.filter(visibility='p') |\
                  queryset.filter(visibility='c') |\
                  queryset.filter(visibility='f', user=self.request.user) |\
                  queryset.filter(visibility='f', user__profile__family=self.request.user) |\
                  queryset.filter(visibility='q', user=self.request.user)
    else:
      ''' Only public objects for anonymous users '''
      queryset =  queryset.filter(visibility='p')
    return queryset
  
  ''' Free text search filter '''
  def filter_freetextsearch(self, queryset, query=None):
    """ Returns the queryset filtered by a free text search query.
        The query is taken from the request, using the key defined in settings.
        If the query is found, it searches for the query in all CharField and TextField fields of the model.
        If the model has ManyToMany fields, it will also search in the related CharField and TextField fields.
        If no query is found, it returns the original queryset
    """
    if not query:
      query = self.get_value_from_request(getattr(settings, 'SEARCH_QUERY_CHARACTER', 'q'), default=False, silent=True)
    if query:
      # Build a Q object for the search query using the provided query string
      q_obj = self.__build_search_query(query, queryset.model)
      # Apply the Q object filter to the queryset
      queryset = queryset.filter(q_obj).distinct()
    # Return the queryset, which is either filtered or the original queryset
    return queryset

  def __get_searchable_fields(self, model):
    """
    Returns a list of fields that can be used for searching in the given model.
    Includes:
    - CharField and TextField fields
    - ManyToMany related CharField/TextField fields
    - If the model has a 'parent' relation, also include the parent model's
      CharField/TextField fields, prefixed with 'parent__'
    """
    fields = []

    for field in model._meta.get_fields():
      if isinstance(field, (CharField, TextField)):
        if self.__field_is_secure(field.name):
          fields.append(field.name)

      elif isinstance(field, ManyToManyField):
        related_model = field.remote_field.model
        for related_field in related_model._meta.fields:
          if isinstance(related_field, (CharField, TextField)):
            if self.__field_is_secure(related_field.name):
              fields.append(f"{field.name}__{related_field.name}")

      elif field.name == "parent" and field.is_relation:
        parent_model = field.related_model
        for parent_field in parent_model._meta.fields:
          if isinstance(parent_field, (CharField, TextField)):
            if self.__field_is_secure(parent_field.name):
              fields.append(f"parent__{parent_field.name}")
    return fields

  def __build_q_for_term_group(self, terms, model):
    """ Builds a Q object for a group of terms, where each term must match
        all searchable fields of the model.
        If no terms are provided, it returns an empty Q object.
    """
    fields = self.__get_searchable_fields(model)
    group_q = Q()
    found = False
    for field in fields:
      field_q = Q()
      for term in terms:
        field_q &= Q(**{f"{field}__icontains": term})
      # Check if the AND query has results, else an empty Q object should be returned
      if model.objects.filter(field_q).exists():
        group_q |= field_q
        found = True
    return group_q if found else Q(pk__in=[])
  
  def __build_search_query(self, query_string, model):
    """ Builds a Q object for a free text search query.
        The query string can contain terms separated by '&&' (AND) and '||' (OR).
        If no query string is provided, it returns an empty Q object.
    """
    if not query_string:
      return Q()
    # Replace custom operators with Django's Q operators, to allow __and__ and __or__ in the query string
    # while also allowing for '&&' (encoded to %26%26) and '||' as logical operators
    query_string = query_string.lower().replace('__and__', '&&').replace('__or__', '||')
    query_string = query_string.lower().replace(' and ', '&&').replace(' or ', '||')
    q_obj = Q()
    or_groups = [group.strip() for group in query_string.split('||') if group.strip()]
    found_valid_group = False
    for group in or_groups:
      and_terms = [term.strip() for term in group.split('&&') if term.strip()]
      group_q = self.__build_q_for_term_group(and_terms, model)
      test_qs = model.objects.filter(group_q)
      if test_qs.exists():
        q_obj |= group_q
        found_valid_group = True
    return q_obj if found_valid_group else Q(pk__in=[])
  

  def search_results(self, queryset, search_fields):
    """ Search results based on specific fields.
        If no search fields are provided, it returns the original queryset.
    """
    for field in search_fields:
      value = self.get_value_from_request(field, default=None, silent=True)
      if value:
        queryset = self.__search_queryset(queryset.model, queryset, field, value)
    return queryset.order_by().distinct()
  
  def __search_queryset(self, model, queryset, field_name, value):
    # Extract last field in relation path
    last_field_name = field_name.split("__")[-1]
    if not self.__field_is_secure(last_field_name):
      return queryset.none()
    # Traverse relations to find the base field model
    base_field = model
    for part in field_name.split("__")[:-1]:
      base_field = base_field._meta.get_field(part).related_model
    field = base_field._meta.get_field(last_field_name) if hasattr(base_field, "_meta") else None
    # Pick lookup operator
    if isinstance(field, (models.CharField, models.TextField)):
      lookup = f"{field_name}__icontains"
      parent_lookup = f"parent__{last_field_name}__icontains"
    else:
      lookup = f"{field_name}__exact"
      parent_lookup = f"parent__{last_field_name}__exact"
    # Always build the base filter
    filters = Q(**{lookup: value})

    # If the model has a self-referential 'parent', include parent filter
    if hasattr(base_field, "_meta") and "parent" in [f.name for f in base_field._meta.get_fields()]:
      filters |= Q(**{parent_lookup: value})
    return queryset.filter(filters)

  
  def exclude_results(self, queryset, exclude_character=None, **kwargs):
    """ Exclude results based on settings.
        If the model has an 'exclude' field, it will exclude objects where exclude=True.
        example: ?exclude=field1:value1,field2:value2
        example: ?exclude=location__slug:home
    """
    if not exclude_character:
      exclude_character = getattr(settings, 'SEARCH_EXCLUDE_CHARACTER', 'exclude')
    exclude_fields = self.get_value_from_request(exclude_character, default='', silent=True).split(',')
    if exclude_fields:
      exclude_fields = [field.strip() for field in exclude_fields if field.strip()]
      for exclusion in exclude_fields:
        key,value = exclusion.split(':') if ':' in exclusion else (exclusion, 'true')
        queryset = queryset.exclude(**{f"{key}__icontains": value})
    return queryset