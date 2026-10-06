# cmnsd documentation

For whoever builds a project on cmnsd, or works on cmnsd itself. What cmnsd is: the [README](../README.md).

## Contents

Read in this order when you're new; each page stands on its own afterwards.

| Page | What it covers |
|---|---|
| [Installation](installation.md) | cmnsd in a project: the submodule, settings, URLs, the base template |
| [Configuration](configuration.md) | Every setting cmnsd reads, with its default |
| [Models](models.md) | The mixins, the base models, composing a model |
| [Status, visibility and access](access.md) | Who sees what, and `filter_accessible` everywhere |
| [The API](api.md) | Registering models, fields and actions; the endpoints; the response |
| [Edit mode](edit-mode.md) | The switch, `can_edit`, editable blocks, child records, the change log |
| [cmnsd.js](javascript/readme.md) | Setting it up, the modules, the `data-cmnsd-*` attributes - a folder of its own |
| [Templates and tags](templates.md) | The templates cmnsd ships, the template tag libraries, the middleware |
| [Accounts](accounts.md) | Sign in, registration and approval, profile, passwords |
| [The admin](admin.md) | Admin mixins and opt-in bulk actions |
| [cmnsd.css](css.md) | The message area, the fonts, the cmnsd mark |
| [Static files](static-files.md) | The included libraries and fonts, hashed file names |
| [Resources](resources.md) | `update.sh` for every deploy, `.post_update.sh`, `pato.sh` for production data |
| [Developing cmnsd](developing.md) | What belongs in cmnsd, branches, tests, releases |

## How a page looks

**One topic per page**, named after the topic in lowercase with hyphens, and listed in the table above.

1. A title, then one or two sentences: what this is and when you need it.
2. Sections in the order someone needs them - setup before use, the common case before the exceptions.
3. Code blocks for commands and settings, so they can be copied as they are.
4. Links to the code (`models/access.py`) rather than copies of it: the code is the detail, the page is the map.

**Keep it:**

- **Short** - under 100 lines. When a page grows past that, it's two topics.
- **True** - written for what's built, not what's planned. Designs, decisions and open questions are development notes, not documentation.
- **In step with the code** - a change that makes a page wrong updates the page in the same commit.
- **Generic** - cmnsd serves more than one project. Examples use made-up models (`Storyline`, `Tag`); a project is named only to show where an idea came from.

## Related

- The project's own documentation - FMLY3: `documentation/developer/`
