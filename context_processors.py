from django.conf import settings

''' Context Processors for CMNS Django Project 

    Add this to your settings.py:
    TEMPLATES = [
      {
        [...]
        'OPTIONS': {
          'context_processors': [
            [...]
            'cmnsdjango.context_processors.setting_data',
          ],
        },
      },
    ]
'''

def setting_data(request):
  ''' Return Context Variables 
      with default fallback values if not set in project/settings.py 
  '''  
  return {
    'project_name': getattr(settings, 'SITE_NAME', 'A CMNS Django Project - backed by cmnsd'),
    'meta_description': getattr(settings, 'META_DESCRIPTION', 'A CMNS Django Project'),#
    'language_code': getattr(settings, 'LANGUAGE_CODE', 'en'),

    'json_load_values': getattr(settings, 'JSON_LOAD_VALUES', False),
    
    'search_query_character': getattr(settings, 'SEARCH_QUERY_CHARACTER', 'q'),
    'search_exclude_character': getattr(settings, 'SEARCH_EXCLUDE_CHARACTER', 'exclude'),
    'search_min_length': getattr(settings, 'SEARCH_MIN_LENGTH', 3),
    'debug': getattr(settings, 'DEBUG', False),
  }