from django import template
register = template.Library()


''' Apply status filter to a queryset '''
@register.filter
def filter_by_status(queryset):
    ''' Add status objects to queryset '''
    queryset = queryset.filter(status='p')
    return queryset

''' Apply visibility filters to a queryset based on the user '''
@register.filter
def filter_by_user(queryset, user):
    ''' Add user objects to queryset '''
    if user.is_authenticated:
      queryset =  queryset.filter(user=user)
    return queryset

@register.filter
def filter_by_visibility(queryset, user):
    ''' Add private objects for current user to queryset '''
    if user.is_authenticated:
      ''' Process visibility filters '''
      queryset =  queryset.filter(visibility='p') |\
                  queryset.filter(visibility='c') |\
                  queryset.filter(visibility='f', user=user) |\
                  queryset.filter(visibility='f', user__profile__family=user) |\
                  queryset.filter(visibility='q', user=user)
      if hasattr(user, 'profile'):
        ''' Process the dislike filter '''
        if user.profile.hide_least_liked:
          if hasattr(queryset.first(), 'slug'):
            queryset = queryset.exclude(slug__in=user.profile.dislike.values_list('slug', flat=True))
          elif 'Comment.Comment' in str(type(queryset.first())):
            queryset = queryset.exclude(location__slug__in=user.profile.dislike.values_list('slug', flat=True))
        ''' Process Ignored Tags '''
        if user.profile.ignored_tags.all().count() > 0:
          if hasattr(queryset.first(), 'tags'):
            queryset = queryset.exclude(tags__in=user.profile.ignored_tags.all()).exclude(tags__parent__in=user.profile.ignored_tags.all())
          elif 'Tag.Tag' in str(type(queryset.first())):
            queryset = queryset.exclude(id__in=user.profile.ignored_tags.values_list('id', flat=True)).exclude(parent__in=user.profile.ignored_tags.all())
          elif 'Comment.Comment' in str(type(queryset.first())):
            queryset = queryset.exclude(location__tags__in=user.profile.ignored_tags.all()).exclude(location__tags__parent__in=user.profile.ignored_tags.all())
    else:
      queryset =  queryset.filter(visibility='p')
    return queryset