# CMNSD

![cmnsd logo](https://raw.githubusercontent.com/arnecoomans/cmnsd/refs/heads/main/static/img/cmnsd/cmnsd.png "cmnsd logo")


This repository contains apps, data and scripts that support running 
CMNS' django projects.

## Helpers
Helper scripts make your django project more manageble. 

## CMNSD app
This app extends Django with abstract models and filter functions that are used in most
CMNS projects. By centralizing these models and reusable views, the maintenance load for
CMNS projects decreases.
- model/basemodel.py
  A model containing the basic features used in most cmns projects such as user, creation-
  and -update date, extending it with status and visibility. Project models can extend these
  model classes.
- views/filter.py
  Based on status and visibility, return a filtered queryset for the specific use-case.
- views/json/
  JSON handling views, offering unified format to supply object or object attributes via JSON,
  supporting basic CRUD
- static/js
  Javascripts to make JSON requests to the app and update the result in pre-defined containers
- templates/objects, templates/attributes
  Default templates to be used when rendering objects via the JSON view


### Installation instructions
@Todo
To use built in templatetags, add the following builtins to your TEMPLATES - OPTIONS - builtins:
- 'django.templatetags.i18n',
- 'cmnsd.templatetags.markdown',
- 'cmnsd.templatetags.query_filters',
- 'cmnsd.templatetags.queryset_filters',
- 'cmnsd.templatetags.text_filters',
#### Checks
Use $ python manage.py check to check if all elements are present in the configuration

### Usage instructions
@Todo

## Configuration in settings.py
These configuration settings are expected by CMNSD. They will all have a default setting

| Setting | Default Value | Suggestion or explenation|
| --- | --- | --- |
| SITE_NAME | 'Vakantieplanner DEVELOPMENT'
| AJAX_BLOCKED_MODELS | [] | |
| AJAX_DEFAULT_DATA_SOURCES | ['kwargs', 'GET', 'POST', 'json', 'headers'] | |
| AJAX_PROTECTED_FIELDS | [] | |
| AJAX_RESTRICTED_FIELDS | [] | |
| AJAX_RENDER_REMOVE_NEWLINES | True | |
| AJAX_ALLOW_FK_CREATION_MODELS | [] | ['comment'] |
| AJAX_ALLOW_RELATED_CREATION_MODELS | [] | ['tag', 'visited in', 'list', 'list-location', 'description', 'link'] |
| AJAX_MAX_DEPTH_RECURSION | 3 | Maximum depth for recursion in nested objects (ForeignKey, ManyToMany, OneToOne) creation, updates and lookups |
| AJAX_MODES | ['editable', 'add'] | Will be added to context.ajax |
| DEFAULT_MODEL_STATUS | 'p' | draft (d), published (p), revoked (r) or deleted (x) |
| DEFAULT_MODEL_VISIBILITY | 'p' | private (q), family (f), community (c) or public (p) |
| SEARCH_EXCLUDE_CHARACTER | 'exclude' | For url structure ?exclude=pk:1 |
| SEARCH_MIN_LENGTH | 2 | |
| SEARCH_QUERY_CHARACTER | 'q' | For url structure ?q=foo |

## Model configuration
| Setting | Default Value | Suggestion or explenation|
| --- | --- | --- |
| disallow_access_fields | [] | Do not allow ajax access to these fields |
| restrict_access_fields | [] | Do not allow unauthenticated access to these fields |
| ajax_template_name | | Default template name when rendering model |
| 

