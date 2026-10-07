#!/bin/bash
# pato - production data to local: copies a site's database and uploaded
# files from the server into the local development copy.
#
# Run it in the project root, through a link: ln -s cmnsd/resources/pato.sh pato.sh
# Configure it in .pato, next to that link (never committed - .gitignore
# both .pato and fixtures/):
#
#   REMOTE_HOST=web06                           an ssh host
#   REMOTE_PATH=/data/www/fmly.cmns.nl          the site on the server
#   LOCAL_PATH=~/Documents/Code/python/fmly     the local project
#   MEDIA_ROOT=private                          uploads, relative to both paths;
#                                               several: MEDIA_ROOT="private other"
#   MEDIA_EXCLUDE="cache/"                      optional: not copied (rsync patterns)
#   DUMP_EXCLUDE="thumbnail"                    optional: apps/models left out of the
#                                               dump, on top of the defaults below
#
# In order:
#   1. dumpdata on the server, streamed straight to fixtures/prod_data.json
#      here - no copy stays on the server. Left out: contenttypes and
#      auth.permission (recreated by migrate) and sessions (production's
#      session keys don't belong on a laptop), plus DUMP_EXCLUDE.
#   2. rsync each MEDIA_ROOT (no --delete: files removed on the server stay).
#   3. Locally: migrate, a dated backup of the local database
#      (fixtures/local_backup-<date>.json), flush, loaddata.
#   4. .post_pato.sh, if there is one and it's executable: the project's
#      own steps afterwards, with the virtual environment active.
#
# Stops at the first error. Everything local is replaced by step 3 - the
# backup is the way back:
#   python manage.py flush --no-input && python manage.py loaddata fixtures/local_backup-<date>.json
#
# Production data is real people's data: it stays in fixtures/ and the
# media folders on this machine, never in git.
#
# Author: Arne Coomans
# Version: 2.0.0

set -euo pipefail

# .pato: in the folder it's run from, else next to the script (or its link).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$PWD/.pato" ]; then
  PATO_FILE="$PWD/.pato"
elif [ -f "$SCRIPT_DIR/.pato" ]; then
  PATO_FILE="$SCRIPT_DIR/.pato"
else
  echo "Error: no .pato found in $PWD or $SCRIPT_DIR."
  echo "Create it in the project root with:"
  echo "  REMOTE_HOST=yourhost"
  echo "  REMOTE_PATH=/data/www/yourapp"
  echo "  LOCAL_PATH=~/path/to/local/project"
  echo "  MEDIA_ROOT=private"
  exit 1
fi
# shellcheck source=/dev/null
source "$PATO_FILE"

: "${REMOTE_HOST:?REMOTE_HOST missing in $PATO_FILE}"
: "${REMOTE_PATH:?REMOTE_PATH missing in $PATO_FILE}"
: "${LOCAL_PATH:?LOCAL_PATH missing in $PATO_FILE}"
: "${MEDIA_ROOT:?MEDIA_ROOT missing in $PATO_FILE}"
MEDIA_EXCLUDE="${MEDIA_EXCLUDE:-}"
DUMP_EXCLUDE="contenttypes auth.permission sessions ${DUMP_EXCLUDE:-}"

cd "$LOCAL_PATH"
PYTHON=".venv/bin/python"
[ -x "$PYTHON" ] || { echo "Error: no virtual environment at $LOCAL_PATH/.venv."; exit 1; }

stamp=$(date +%Y%m%d-%H%M%S)
mkdir -p fixtures
chmod 700 fixtures
trap 'rm -f "fixtures/prod_data-$stamp.part"' EXIT   # a dump cut short

dump_args="--natural-foreign --natural-primary"
for label in $DUMP_EXCLUDE; do
  dump_args="$dump_args --exclude $label"
done

# --- 1. The database, from the server ----------------------------------------

echo "Dumping the database on $REMOTE_HOST..."
ssh "$REMOTE_HOST" "cd '$REMOTE_PATH' && .venv/bin/python manage.py dumpdata $dump_args" > "fixtures/prod_data-$stamp.part"
mv "fixtures/prod_data-$stamp.part" fixtures/prod_data.json   # only a complete dump replaces the last one
chmod 600 fixtures/prod_data.json
echo "Dump: $(du -h fixtures/prod_data.json | cut -f1)."

# --- 2. The uploaded files ------------------------------------------------------

rsync_excludes=()
for pattern in $MEDIA_EXCLUDE; do
  rsync_excludes+=(--exclude "$pattern")
done
for root in $MEDIA_ROOT; do
  echo "Syncing $root/..."
  mkdir -p "$root"
  # ${a[@]+"${a[@]}"}: an empty array under set -u, in macOS's bash 3.2
  rsync -chazP --stats ${rsync_excludes[@]+"${rsync_excludes[@]}"} "$REMOTE_HOST:$REMOTE_PATH/$root/" "$root/"
done

# --- 3. The local database ------------------------------------------------------

echo "Migrating the local database..."
"$PYTHON" manage.py migrate --no-input

echo "Backing up the local database to fixtures/local_backup-$stamp.json..."
# shellcheck disable=SC2086 - dump_args is a list of words on purpose
"$PYTHON" manage.py dumpdata $dump_args > "fixtures/local_backup-$stamp.json"
chmod 600 "fixtures/local_backup-$stamp.json"

echo "Flushing the local database..."
"$PYTHON" manage.py flush --no-input

echo "Loading the production data..."
"$PYTHON" manage.py loaddata fixtures/prod_data.json

# --- 4. The project's own steps -------------------------------------------------

if [ -x ".post_pato.sh" ]; then
  echo "Running .post_pato.sh..."
  # shellcheck source=/dev/null
  source .venv/bin/activate
  ./.post_pato.sh
elif [ -f ".post_pato.sh" ]; then
  echo "Warning: .post_pato.sh is not executable (chmod +x .post_pato.sh) - skipped."
fi

echo "Done. The previous local data: fixtures/local_backup-$stamp.json"
