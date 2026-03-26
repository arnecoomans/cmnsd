# Pato

Pato syncs data from a remote environment (production, acceptance) to a local project. It generates a Django fixture on the remote host, pulls it down along with media files, and loads it into the local database.

The name comes from the Dutch word for pipe — it pipes data from one place to another.

## Requirements

- SSH key-based access to the remote host (no password prompt)
- `.venv/` present in both local and remote project roots
- The remote project must be a Django project with `manage.py`

## Setup

Create a `.pato` file in the project root (it is gitignored):

```ini
REMOTE_HOST=web06
REMOTE_PATH=/data/www/yourapp.example.com
LOCAL_PATH=~/Documents/Code/python/yourapp
MEDIA_ROOT=public
```

| Variable | Description |
|---|---|
| `REMOTE_HOST` | SSH host alias or IP of the remote server |
| `REMOTE_PATH` | Absolute path to the Django project on the remote |
| `LOCAL_PATH` | Absolute path to the Django project locally |
| `MEDIA_ROOT` | Media directory name, assumed identical on remote and local |

## Usage

```bash
./pato.sh
```

## What it does

1. SSHes into the remote host and runs `manage.py dumpdata` into `fixtures/data.json`
2. Creates `fixtures/` and `{MEDIA_ROOT}/` locally if they do not exist
3. Rsyncs `fixtures/` from remote to local
4. Rsyncs `{MEDIA_ROOT}/` from remote to local
5. Runs `manage.py loaddata fixtures/data.json` using the local `.venv`

The fixture is a full database dump using natural keys (`--natural-foreign --natural-primary`), making it portable across SQLite, PostgreSQL, and MySQL.

## Files

| File | Description |
|---|---|
| `pato.sh` | The sync script (gitignored) |
| `.pato` | Environment config (gitignored) |
| `fixtures/data.json` | Generated fixture, not committed |
| `cmnsd/resources/pato.sh` | Canonical source — copy to project root to use |
