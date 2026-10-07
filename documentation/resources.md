# Resources

Two shell scripts in `resources/` that every cmnsd project uses on its server and in development: `update.sh` deploys an update, `pato.sh` pulls production data into a local copy.

## update.sh - every deploy

Link it into the project root once:

```sh
ln -s cmnsd/resources/update.sh update.sh
```

Then a deploy is `./update.sh`, in the project's directory on the server. In order:

1. **Pull** the project.
2. **Submodules:** initialise them, check each out on the branch in `.gitmodules` (`main` when none is set), and pull that branch (`git submodule update --remote --merge`).
3. **Requirements:** with the project's `.venv` active, `pip install -r requirements.txt` - only when a `requirements.txt` changed, in the project or a submodule. It installs the project's file, so that file includes cmnsd's with a line `-r cmnsd/requirements.txt`.
4. **`migrate`** and **`collectstatic`**, always: both are cheap when nothing changed, and a missed `collectstatic` breaks pages with hashed file names ([Static files](static-files.md)).
5. **`.post_update.sh`**, the project's own steps, if there is one.
6. **Restart:** `sudo supervisorctl restart <name>`, the program named after the directory's first part (`www.example.org` -> `www`, `fmly.example.org` -> `fmly`).

Any failing step stops the script before the restart, so the running site keeps its last working state. Changes are detected by comparing commits before and after, not by reading git's output.

**Step 2 follows the branch, not the recorded commit.** A project gets the newest commit of its cmnsd branch on every deploy. To keep a project on a fixed cmnsd, give it a branch of its own in `.gitmodules` and move that branch only on purpose:

```ini
[submodule "cmnsd"]
  path = cmnsd
  url = https://github.com/arnecoomans/cmnsd.git
  branch = fmly
```

## .post_update.sh - the project's own steps

Optional, in the project root, executable (`chmod +x`), versioned with the project. It runs with the virtual environment active, just before the restart, and gets `UPDATE_CHANGED=1` when the pull brought changes, else `0`. Each step should be safe to repeat:

```sh
#!/bin/bash
set -e
python manage.py create_default_pages
python manage.py check --deploy
```

Not executable: skipped with a warning. Failing: no restart.

## pato.sh - production data in development

Copies the production database and uploaded files into the local copy, to develop against real data. Run it on the development machine, in the project root, through a link:

```sh
ln -s cmnsd/resources/pato.sh pato.sh
./pato.sh
```

Settings in `.pato` in the project root. `.gitignore` both `.pato` and `fixtures/` - the dumps hold every account with its password hash:

```sh
REMOTE_HOST=web06                          # an ssh host
REMOTE_PATH=/data/www/fmly.example.org     # the site on the server
LOCAL_PATH=~/code/fmly                     # the local project
MEDIA_ROOT=private                         # the uploads; several: "private other"
MEDIA_EXCLUDE="cache/"                     # optional: not copied - here, generated thumbnails
DUMP_EXCLUDE="thumbnail"                   # optional: also left out of the dump
```

Only uploads are copied. Static files (`public/static/`) come from the code: in development `runserver` serves them.

In order, stopping at the first error:

1. **The database:** `dumpdata` on the server, streamed straight into `fixtures/prod_data.json` - no copy stays on the server. Left out: `contenttypes` and `auth.permission` (`migrate` recreates them), `sessions` (production's session keys don't belong on a laptop), and `DUMP_EXCLUDE`.
2. **The files:** `rsync` of each `MEDIA_ROOT`, without `--delete`.
3. **Locally:** `migrate`, a backup of the local database (`fixtures/local_backup-<date>.json`), then **flush** and `loaddata`.
4. **`.post_pato.sh`**, if there is one and it's executable: the project's own steps afterwards, with the virtual environment active - the counterpart of `.post_update.sh`.

Everything local is replaced; the dated backup is the way back:

```sh
python manage.py flush --no-input && python manage.py loaddata fixtures/local_backup-<date>.json
```

A project with sorl-thumbnail leaves both its cache folder and its `thumbnail` table out: the copy then makes its own thumbnails, instead of pointing at cache files that weren't copied.
