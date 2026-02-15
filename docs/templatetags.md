# Templatetag documentation
This document explains and documents the use of the custom cmnsd templatetags.
Templatetags are sorted by origin file


## humanize_date
Convert a date or datetime into a human-readable string.
- If the date is within HUMANIZE_DATE_MAX_DAYS (default: 365 days)
  - returns a relative expression like "3 days ago" or "in 2 weeks".
- Otherwise → formats the date using Django settings or a provided format.

Example:
```
{{ description.date_created|humanize_date:"j F Y" }}
```

## Markdown
Returns the input as Markdown parsed to HTML. Append with |safe to not escape
special characters, so html is passed to the browser.

Example:
```
{{ description|markdown|safe }}
```

## query_filters
Process request query parameters.

### update_query_params
Updates the query parameters with the supplied information. Allows to add, remove or replace a 
query parameter, while keeping the existing parameters. Requires request to be passed to the
template tag to be able to read existing query parameters.

Example:
```
<a href="{% url 'baseurl' %}{% update_query_params request add='tag1' to='tags' %}">Add tag1</a>
<a href="{% url 'baseurl' %}{% update_query_params request remove='tag1' to='tags' %}">Remove tag1</a>
<a href="{% url 'baseurl' %}{% update_query_params request replace='newvalue' to='category' %}">Replace category with newvalue</a>
```

## Queryset filters
Process a queryset and return the processed value.

### filter_by_status
Filter the queryset by "status=p"

### filter_by_user
Requires: user object
If the user is authenticated, return all objects by the supplied user

### filter_by_visibility
Requires: current user object
Returns the queryset filtered on visibility parameters, so seeing
public, community, and family when user is configured as family 
and it's private objects.

### without
Requires: an object or queryset to remove from queryset
Returns the queryset without the mentioned object or queryset objects.
Usefull to list overlap between relations.

### match_queryset
Requires: an object or queryset to remove from queryset
Returns the queryset overlap between the originial queryset and the
argument. Replaces a for-loop checking if a value is inside a larger
queryset. 
