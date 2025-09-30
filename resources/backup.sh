#!/usr/bin/env bash
#
# backup.sh
#
# Creates compressed backups of directories inside a source directory.
# Supports weekly, monthly, and yearly backups, with configurable retention.
#
# Usage:
#   ./backup.sh <frequency> <source_dir> <target_dir>
#
# Arguments:
#   frequency   weekly|monthly|yearly
#   source_dir  path to source (e.g. /data)
#   target_dir  path to backup root (e.g. /backup)
#
# Example:
#   ./backup.sh weekly /data /backup
#

set -euo pipefail

FREQ="$1"
SRC_DIR="$2"
DEST_ROOT="$3"

# Validate frequency
if [[ "$FREQ" != "weekly" && "$FREQ" != "monthly" && "$FREQ" != "yearly" ]]; then
  echo "Error: Frequency must be weekly, monthly, or yearly."
  exit 1
fi

# Ensure directories exist
if [[ ! -d "$SRC_DIR" ]]; then
  echo "Error: Source directory $SRC_DIR does not exist."
  exit 1
fi

DEST_DIR="$DEST_ROOT/$FREQ"
mkdir -p "$DEST_DIR"

# Generate timestamp (week number, month, or year)
case "$FREQ" in
  weekly)
    TS=$(date +%Y-%V)   # e.g., 2025-39 (ISO week)
    RETENTION="+42"     # 6 weeks * 7 days
    ;;
  monthly)
    TS=$(date +%Y-%m)   # e.g., 2025-09
    RETENTION="+548"    # ~18 months (548 days)
    ;;
  yearly)
    TS=$(date +%Y)      # e.g., 2025
    RETENTION=""        # keep forever
    ;;
esac

# Backup each subdirectory inside SRC_DIR
for DIR in "$SRC_DIR"/*/; do
  BASENAME=$(basename "$DIR")
  TARFILE="$DEST_DIR/${BASENAME}_${TS}.tar.gz"
  echo "Creating backup for $DIR -> $TARFILE"
  tar -czf "$TARFILE" -C "$SRC_DIR" "$BASENAME"
done

# Remove old backups if retention is defined
if [[ -n "$RETENTION" ]]; then
  echo "Cleaning up backups older than $RETENTION days in $DEST_DIR"
  find "$DEST_DIR" -type f -name "*.tar.gz" -mtime "$RETENTION" -print -delete
fi

echo "Backup for $FREQ completed successfully."
