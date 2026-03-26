# update.sh

Server-side deployment script for Django applications. Pulls the latest code from Git, updates submodules if present, and conditionally runs migrations, installs requirements, collects static files, and restarts the application via Supervisor.

**Version:** 1.2.2

## Requirements

- Git repository with an upstream remote
- Supervisor managing the application process
- `.venv/` in the project root
- `sudo` access for `supervisorctl restart`

## Usage

```bash
bash update.sh
```

Run from anywhere inside the repository — the script resolves the root automatically via `git rev-parse --show-toplevel`.

## What it does

### 1. Git pull

Pulls the latest changes from the upstream remote. Exits on failure.

### 2. cmnsd standalone update

If a `cmnsd/` directory exists with its own `.git` and is **not** listed as a submodule in `.gitmodules`, it is pulled separately. This handles the case where `cmnsd` is included as a plain directory clone rather than a submodule.

### 3. Submodule updates

If `.gitmodules` exists, all submodules are updated in this order:

1. `git submodule update --init --recursive` — initialise any new submodules
2. `git submodule foreach` — checkout each submodule's configured branch (defaults to `main`)
3. `git submodule update --remote --merge` — pull the latest commit from each tracked branch
4. `git diff --submodule=log` — record what changed for the conditional checks below
5. `git submodule update --init --recursive` — reinitialise to ensure consistency

### 4. Conditional steps

The combined output of the git pull and submodule diff is scanned for keywords. Each step only runs if its trigger is detected:

| Trigger keyword | Action |
|---|---|
| `requirements.txt` | `pip install -r requirements.txt` |
| `migration` | `python manage.py migrate` |
| `static` | `python manage.py collectstatic --noinput` |

If none of these keywords appear, all three steps are skipped.

### 5. Supervisor restart

The Supervisor pool name is derived from the project directory name — everything before the first `.`:

```
camping.cmns.nl  →  camping
```

Then runs:

```bash
sudo supervisorctl restart <pool_name>
```

## Assumptions

- The virtual environment is at `.venv/` in the project root
- The Supervisor pool name matches the first segment of the directory name
- Submodules track a branch named in `.gitmodules` (falls back to `main`)
