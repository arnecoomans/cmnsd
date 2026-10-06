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

Copies the production database and uploaded files into a local copy, to develop against real data. Run it on the development machine. Configure it in a `.pato` file next to the script - never committed:

```sh
REMOTE_HOST=www.example.org        # an ssh host
REMOTE_PATH=/data/www/example.org
LOCAL_PATH=~/code/example
MEDIA_ROOT=public                  # the uploads folder, relative to both paths
```

It then:

1. Runs `dumpdata` on the server into `fixtures/prod_data.json` (natural keys).
2. Copies the fixtures and the media folder with `rsync`.
3. Backs up the local database to `fixtures/local_backup.json`.
4. **Flushes the local database** and loads the production data.

Everything local is replaced. The backup in step 3 is the way back:

```sh
python manage.py flush --no-input && python manage.py loaddata fixtures/local_backup.json
```

Production data in development is real people's data: keep `fixtures/` and the media folder out of git, and the copy on your own machine.
