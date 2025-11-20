# Backup Script

This script automates weekly, monthly, and yearly backups of a source directory.

## Features

- Creates a `.tar.gz` archive for each subdirectory in the source directory.
- Stores backups in `/backup/<frequency>/` (or any custom target directory).
- Deletes old backups automatically (6 weeks for weekly, 18 months for monthly).
- Works well with `cron` for scheduling.

## Usage

```bash
./backup.sh <frequency> <source_dir> <target_dir>

# ------------------------------------------------------------
# Automated backups (weekly, monthly, yearly)
# Script: /usr/local/bin/backup.sh
# Source: /data
# Target: /backup
# ------------------------------------------------------------

# Weekly backup — every Sunday at 02:00
0 2 * * 0 /data/resources/cmnsd/resources/backup.sh weekly /data /backup >/dev/null 2>&1

# Monthly backup — first day of the month at 03:00
0 3 1 * * /data/resources/cmnsd/resources/backup.sh monthly /data /backup >/dev/null 2>&1

# Yearly backup — January 1st at 04:00
0 4 1 1 * /data/resources/cmnsd/resources/backup.sh yearly /data /backup >/dev/null 2>&1