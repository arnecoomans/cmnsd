![cmnsd](static/cmnsd.css/branding/cmnsd.png)

Welcome to cmnsd 3: a ground-up rewrite of the shared foundation under CMNS' Django projects.

**cmnsd** is a reusable Django app that holds everything a project needs but isn't specific to it: models that know who may see them, an API that serves them, edit mode to change them on the page, a JavaScript layer that ties it together, and the templates that go with it. A project adds its own models and pages on top; cmnsd keeps the plumbing the same everywhere.

cmnsd 3 is built for and first used by [FMLY3](https://github.com/arnecoomans/fmly). Projects on cmnsd 2 (release 26.09 and before) move to it one by one.

## Models
Small mixins instead of one base model that does everything: a model takes only what it needs.
- **Timestamps, tokens and slugs** - created and modified dates, an unguessable token for URLs and the API, a readable slug.
- **Status** - concept, published, revoked, deleted - and **visibility** - public, community, family, private. Together they decide who sees a row; `filter_accessible()` applies both in one call.
- **Ownership**, **partial dates** (a year without a day, "ca. 1950", "before 1950"), **hierarchies** ("Media: Book" becomes Book under Media) and **translation aliases** (a tag findable in every language).
- **Base models** for tags, comments and preferences, and a ready-made multilingual **Page** for the cookie statement and its kind.

## The API
Nothing is exposed until a model says so. `@api_model` registers a model, `@api_field` exposes a value, `@api_action` exposes a change. Every endpoint checks status and visibility first and answers in one JSON shape, success or error, with display-ready HTML rendered from the project's own templates.

## Edit mode
A switch in the header for anyone who may change something. While it's on, pages show their edit controls - a block of fields opens as a form in place, saves through the API and is checked against changes made in the meantime. While it's off, a page is exactly what every visitor sees. Every change is written to the admin history.

## cmnsd.js
Plain ES modules, no build step and no jQuery. Each module enhances markup marked with `data-cmnsd-*` attributes: live search and filtering, edit blocks and dialogs, pickers, uploads, an image viewer, collapsible sections that remember their state, messages. Without JavaScript every page still works.

## Also included
- **Accounts** - sign in and out, registration with optional approval, profile, password change and reset.
- **Admin mixins** that pair with the model mixins: filters, read-only fields and opt-in bulk actions.
- **Template tags** - safe markdown, search highlighting, query string helpers, an A-Z index, names as the viewer may see them.
- **Middleware** - each user's own language, minified HTML in production.
- **Hashed static files**, so a browser never keeps running an old script.
- **Deploy scripts** - `update.sh` for every update, `pato.sh` to pull production data into development.

## Privacy
cmnsd loads nothing from other sites: Bootstrap, Bootstrap Icons, jQuery and the Inter and Geist fonts are included, so a visit shares nothing with third parties. Objects are identified by token, never by a sequential id, and the API only filters on what a model declares - it can't be used to ask questions about rows the viewer can't see.

## More information
- Documentation: [documentation/readme.md](documentation/readme.md)
