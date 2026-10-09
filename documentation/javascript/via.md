# Via

How you got to a page: arriving from a tag's page at a photo, that tag stands out among the photo's tags - and is the way back. One level deep. `static/cmnsd.js/via.js`.

## The page you come from

Mark a region whose links should say where they came from:

```django
<section data-cmnsd-via-links="tag:{{ tag.token }}">
  ... people, content ...
</section>
```

Every link to another page inside it gets `?via_tag=<token>` (`via_<kind>`, from the attribute). Left alone: anchors, file downloads, API addresses, and links that already carry a `via_`. Links outside a region stay as they are - a header, a breadcrumb.

A region that holds sections of its own layout (collapsible sections in a column) can be a wrapper with `display: contents` - it marks, without a box.

## The page you arrive at

Mark what can be highlighted:

```django
<a class="tag" href="..." data-cmnsd-via="tag:{{ tag.token }}" data-cmnsd-via-title="{% translate 'you came here through this tag' %}">
```

An element whose `kind:token` matches a `via_<kind>` in the address gets the class `is-via` - the project's CSS makes it stand out. `data-cmnsd-via-title` is added to its tooltip.

## Rules

- **One level deep:** the parameter is only added on the region's page. On the page you arrive at, links are clean again - unless it has regions of its own, which then say where *they* lead from.
- **Per element** (`enhance.js`): links in content loaded later (an opened section, a live list) get the parameter too, and an element that arrives later (deferred tags) is still found.
- **Nothing to see:** a token the viewer can't see on the page highlights nothing - the page decides what's on it.
- **Without JavaScript:** plain links, no highlight.
