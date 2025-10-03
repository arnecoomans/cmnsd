# CMNSD

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
- 'cmnsd.templatetags.markdown',
- 'cmnsd.templatetags.query_filters',
- 'cmnsd.templatetags.queryset_filters',
- 'cmnsd.templatetags.text_filters',

### Usage instructions
@Todo

## Configuration
### Queryset
- SEARCH_QUERY_CHARACTER = 'q'
- SEARCH_EXCLUDE_CHARACTER = 'exclude'
- SEARCH_BLOCKED_FIELDS = []
### Json
- JSON_BLOCKED_MODELS = []
- JSON_PROTECTED_FIELDS = []
- JSON_RENDER_REMOVE_NEWLINES =[]


