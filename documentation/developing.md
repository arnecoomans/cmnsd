# Developing cmnsd

For changes to cmnsd itself. cmnsd has no project of its own: it's developed inside the project that needs the change, as that project's submodule.

## What belongs in cmnsd

- **cmnsd never imports a project.** No project models, no project settings beyond what it reads with `getattr(settings, ..., default)`.
- **Something moves into cmnsd once a second use shows what's generic about it** - a mixin, an endpoint, a cmnsd.js module. Until then it stays in the project.
- **Projects hook into cmnsd, not the other way round:** a model defines `api_search_q`, `api_edit_forms` or `can_edit`; a template sets a data attribute cmnsd.js reads.
- **Examples in code and documentation are generic.** A project is named only to say where an idea came from.

## Working in the submodule

```sh
cd cmnsd
git switch fmly                 # the project's cmnsd branch
# ... change, test ...
git commit -am "..."            # commit in cmnsd first
git push
cd ..
git add cmnsd                   # then record the new cmnsd commit in the project
git commit -m "Update cmnsd"
```

Push cmnsd before the project: a project commit pointing at a cmnsd commit that isn't on GitHub can't be checked out anywhere else.

- A change to a **model** needs a migration in `migrations/`: `python manage.py makemigrations cmnsd`.
- A change to **cmnsd.js or cmnsd.css** reaches the server through `collectstatic`, which `update.sh` always runs.
- A change that makes a page in `documentation/` wrong updates it in the same commit.
- **Translations:** cmnsd's strings are translated in the project's `locale/` for now.

## Tests

`tests.py` covers what cmnsd does on its own: the language middleware, edit mode, the API response shape, remembered UI state. They run inside a project, with the project's own tests:

```sh
python manage.py test cmnsd
```

They don't import project apps: the project's `Preferences` is found through the user model (`get_user_model().preferences.related.related_model`). Most of cmnsd is also covered by the project's tests of its own pages and API use.

## System checks

`checks/ApiChecks.py` turns API registration mistakes into errors at startup instead of at the first request. Add a check when a mistake would otherwise only show at request time; give it an id `cmnsd.<area>.E<nnn>` or `W<nnn>`.

## Branches and releases

| | |
|---|---|
| `main` | The current release |
| `fmly` | Development of cmnsd 3, for FMLY3 - the newest |
| Releases | Tagged on GitHub by date: `26.04`, `26.09` (the last cmnsd 2) |

Projects follow a branch ([Resources](resources.md)): a project on `main` gets every new release on its next deploy. A project that must not move gets its own branch, moved on purpose.

## Development notes

Designs, decisions and open questions are kept in `docs/`, which stays out of the repository (`.gitignore`). They explain why; `documentation/` says what and how, and is all a reader of the repository gets - so a decision that changes how cmnsd is used ends up here too.
