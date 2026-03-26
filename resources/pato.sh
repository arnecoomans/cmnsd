#!/bin/bash
# Sync production data to local environment
# Configure via .pato in the project root

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATO_FILE="$SCRIPT_DIR/.pato"

if [ ! -f "$PATO_FILE" ]; then
  echo "Error: .pato config file not found at $PATO_FILE"
  echo "Create it with:"
  echo "  REMOTE_HOST=yourhost"
  echo "  REMOTE_PATH=/data/www/yourapp"
  echo "  LOCAL_PATH=~/path/to/local/project"
  echo "  MEDIA_ROOT=public"
  exit 1
fi

source "$PATO_FILE"

echo "Starting sync from $REMOTE_HOST:$REMOTE_PATH"

echo "Generating fixtures on remote..."
ssh "$REMOTE_HOST" "mkdir -p $REMOTE_PATH/fixtures && cd $REMOTE_PATH && .venv/bin/python manage.py dumpdata --natural-foreign --natural-primary --indent 2 > fixtures/data.json"

if [ $? -ne 0 ]; then
  echo "Error: fixture generation failed on remote."
  exit 1
fi

echo "Ensuring local fixtures directory exists..."
mkdir -p "$LOCAL_PATH/fixtures"

echo "Syncing fixtures..."
rsync -chavzP --stats "$REMOTE_HOST:$REMOTE_PATH/fixtures/" "$LOCAL_PATH/fixtures/"

echo "Ensuring local media directory exists..."
mkdir -p "$LOCAL_PATH/$MEDIA_ROOT"

echo "Syncing media files ($MEDIA_ROOT)..."
rsync -chavzP --stats "$REMOTE_HOST:$REMOTE_PATH/$MEDIA_ROOT/" "$LOCAL_PATH/$MEDIA_ROOT/"

echo "Loading fixtures into local database..."
cd "$LOCAL_PATH" && .venv/bin/python manage.py loaddata fixtures/data.json

if [ $? -ne 0 ]; then
  echo "Error: loaddata failed."
  exit 1
fi

echo "Done."
