#!/usr/bin/env bash
#
# backup.sh
#
# Creates compressed backups of directories inside a source directory.
# Supports weekly, monthly, and yearly backups, with configurable retention.
# Adds duplicate detection, dry-run mode, logging, zstd compression,
# and prevents deletion of the last existing backup for any directory.
#
# Usage:
#   ./backup.sh [--dry-run] <frequency> <source_dir> <target_dir>
#
# Example:
#   ./backup.sh weekly /data /backup
#   ./backup.sh --dry-run weekly /data /backup
#

set -euo pipefail

LOGFILE="/var/log/backup.log"

log() {
  echo "$@" | tee -a "$LOGFILE"
}

# --- Optional --dry-run flag ---
DRYRUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRYRUN=true
  shift
  log "DRY-RUN mode activated (no files will be written or deleted)"
fi

FREQ="$1"
SRC_DIR="$2"
DEST_ROOT="$3"

# Validate frequency
if [[ "$FREQ" != "weekly" && "$FREQ" != "monthly" && "$FREQ" != "yearly" ]]; then
  log "Error: Frequency must be weekly, monthly, or yearly."
  exit 1
fi

# Validate source dir
if [[ ! -d "$SRC_DIR" ]]; then
  log "Error: Source directory $SRC_DIR does not exist."
  exit 1
fi

DEST_DIR="$DEST_ROOT/$FREQ"
[[ "$DRYRUN" == false ]] && mkdir -p "$DEST_DIR"

# Frequency timestamps and retention
case "$FREQ" in
  weekly)
    TS=$(date +%Y-%V)
    RETENTION="+42"   # 6 weeks
    ;;
  monthly)
    TS=$(date +%Y-%m)
    RETENTION="+548"  # ~18 months
    ;;
  yearly)
    TS=$(date +%Y)
    RETENTION=""      # keep forever
    ;;
esac

log "=== Backup run: $FREQ @ $(date) ==="
log "Source: $SRC_DIR"
log "Destination: $DEST_DIR"
log "Timestamp: $TS"
log ""

# --- Backup each directory ---
for DIR in "$SRC_DIR"/*/; do
  BASENAME=$(basename "$DIR")
  TMPFILE=$(mktemp)

  log "--- Processing: $BASENAME ---"
  log "Creating temporary archive (zstd)..."

  # Create tar.zst archive
  tar -c --use-compress-program=zstd -f "$TMPFILE" -C "$SRC_DIR" "$BASENAME"

  # Find last backup
  LASTFILE=$(ls -1t "$DEST_DIR/${BASENAME}_"*.tar.zst 2>/dev/null | head -n 1 || true)

  if [[ -n "$LASTFILE" ]]; then
    log "Found previous backup: $LASTFILE"
    log "Comparing hashes..."

    NEW_HASH=$(sha256sum "$TMPFILE" | awk '{print $1}')
    OLD_HASH=$(sha256sum "$LASTFILE" | awk '{print $1}')

    if [[ "$NEW_HASH" == "$OLD_HASH" ]]; then
      log "No changes detected — skipping backup for $BASENAME."
      rm "$TMPFILE"
      log ""
      continue
    else
      log "Changes detected — storing new backup."
    fi
  else
    log "No previous backup found — creating first backup."
  fi

  TARFILE="$DEST_DIR/${BASENAME}_${TS}.tar.zst"

  if [[ "$DRYRUN" == true ]]; then
    log "[DRY-RUN] Would save: $TARFILE"
    rm "$TMPFILE"
  else
    mv "$TMPFILE" "$TARFILE"
    log "Backup saved: $TARFILE"
  fi

  log ""
done

# --- Safe retention logic ---
if [[ -n "$RETENTION" ]]; then
  log "Starting retention cleanup (older than $RETENTION days)..."

  for SAMPLE in "$SRC_DIR"/*/; do
    BASENAME=$(basename "$SAMPLE")

    # All backups for this directory
    FILES=( "$DEST_DIR/${BASENAME}_"*.tar.zst )
    FILECOUNT=${#FILES[@]}

    # If no files, skip (no previous backup)
    if (( FILECOUNT == 0 )); then
      continue
    fi

    # Never delete the last backup
    if (( FILECOUNT == 1 )); then
      log "Skipping retention for $BASENAME — only one backup exists."
      continue
    fi

    # Otherwise perform retention, but only on old files
    if [[ "$DRYRUN" == true ]]; then
      find "$DEST_DIR" -type f -name "${BASENAME}_*.tar.zst" \
           -mtime "$RETENTION" -print |
        sed 's/^/[DRY-RUN] Would delete: /' | tee -a "$LOGFILE"
    else
      find "$DEST_DIR" -type f -name "${BASENAME}_*.tar.zst" \
           -mtime "$RETENTION" -print -delete | tee -a "$LOGFILE"
    fi
  done

  log "Retention cleanup complete."
fi

log ""
log "Backup for $FREQ completed successfully."
log "========================================="