# cmnsd Resources

This directory contains maintenance and deployment scripts used in Django projects that include **cmnsd** as a submodule or dependency.  
These scripts automate update, deployment, and backup routines for projects managed via `git`, `venv`, and `supervisor`.

---

## 🧩 Overview

| Script | Language | Description |
|--------|-----------|-------------|
| [`update.py`](./update.py) | Python | Smart update utility for Django projects with submodules. Handles git pulls, virtualenv updates, migrations, static file collection, and supervisor restarts. |
| [`update.sh`](./update.sh) | Bash | Lightweight alternative update script for server environments. Designed for quick deployments and auto-handling the `cmnsd` submodule. |

---

## ⚙️ `update.py`

### Purpose
This script performs a **full smart update** of a Django project using `cmnsd`:

- Pulls the latest changes from the main repository.
- Detects and updates git submodules recursively.
- Detects whether requirements, migrations, or static files have changed.
- Activates the virtual environment (`.venv/`).
- Runs `pip install -r requirements.txt` when needed.
- Applies migrations and collects static files when changes are detected.
- Restarts the Django application via `supervisorctl`.

### Usage

Run from the project root (or via symlinked `/update.py`):

```bash
sudo python /update.py
```

or directly (if located in project root):

```bash
sudo python cmnsd/resources/update.py
```

### Notes

- The script automatically detects the `manage.py` location, even if called through a symlink.
- Non-editable fields and submodule updates are handled gracefully.
- The supervisor pool name is derived from the current directory name (before the first dot).

---

## 🧰 `update.sh`

### Purpose
A simplified Bash version for production servers — ideal for manual updates, hotfixes, or deployments without Python dependencies.

- Pulls the latest git changes.
- Detects and updates submodules recursively.
- Automatically performs a `git pull` inside the `cmnsd/` submodule if present.
- Activates `.venv` and installs requirements, applies migrations, and collects static files only if changes are detected.
- Restarts the Django app via `supervisorctl`.

### Usage

Run from any directory within the project:

```bash
sudo bash cmnsd/resources/update.sh
```

### Example output

```text
Pulling latest changes from Git...
Changes detected in the main repository.
Detected local submodule 'cmnsd'. Pulling latest changes...
cmnsd submodule updated successfully.
Changes detected in requirements, migrations, static files, or submodules.
Activating virtual environment...
Installing new requirements...
Running migrations...
Collecting static files...
Restarting application with supervisor for pool 'project'...
Application restart for pool 'project' complete.
```

### Version

Current version: **1.2.1**

---

## 🔧 Supervisor Integration

Both update scripts use the current directory name (before the first dot) to determine the supervisor pool name:

```bash
pool_name=$(basename "$PWD" | cut -d. -f1)
```

Example:
- Directory `/srv/sites/example.com` → Supervisor pool: `example`
- Directory `/srv/projects/fmly` → Supervisor pool: `fmly`

Ensure your supervisor configuration matches this naming convention.

---

## 🗂 Folder Purpose Summary

| File | Purpose |
|------|----------|
| `update.py` | Full-featured Python-based update automation for Django projects |
| `update.sh` | Lightweight Bash-based update script for quick deployments |
| *(optional future scripts)* | Backup utilities, environment checks, and admin helpers |

---

## 🧑‍💻 Author

**Arne Coomans**
