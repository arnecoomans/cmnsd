# Backup Script

This script automates weekly, monthly, and yearly backups of a source directory using a Python-based workflow.

## Features

- Creates a `.tar.zst` archive for each subdirectory in the source directory.
- Stores backups in `/backup/<frequency>/` (or any custom target directory).
- Skips creating a new backup when nothing has changed (hash-based duplicate detection).
- Deletes old backups automatically (6 weeks for weekly, ~18 months for monthly), while **never deleting the last backup** of any directory.
- Logs to `/var/log/backup.log`.
- Sends email alerts on failures (using `mail` and `ADMIN_EMAIL` from `/etc/backup.conf`).
- Works well with `cron` for scheduling.
- Supports a `--dry-run` mode.

## Usage

```bash
./backup.py [--dry-run] <frequency> <source_dir> <target_dir>
```

# Examples
```
./backup.py weekly /data /backup
./backup.py --dry-run monthly /data /backup
```

* frequency: weekly, monthly, or yearly
* source_dir: directory to back up (e.g. /data)
* target_dir: root backup directory (e.g. /backup)

# Configuration

Create /etc/backup.conf:
```
ADMIN_EMAIL="post+web06@arnecoomans.nl"
```
Ensure appropriate permissions:
```bash
sudo chmod 600 /etc/backup.conf
sudo chown root:root /etc/backup.conf
```
# Example Cron Jobs

```
# ------------------------------------------------------------
# Automated backups (weekly, monthly, yearly)
# Script: /data/resources/cmnsd/resources/backup.py
# Source: /data
# Target: /backup
# ------------------------------------------------------------

# Weekly backup — every Sunday at 02:00
0 2 * * 0 /usr/bin/python3 /data/resources/cmnsd/resources/backup.py weekly /data /backup >/dev/null 2>&1

# Monthly backup — first day of the month at 03:00
0 3 1 * * /usr/bin/python3 /data/resources/cmnsd/resources/backup.py monthly /data /backup >/dev/null 2>&1

# Yearly backup — January 1st at 04:00
0 4 1 1 * /usr/bin/python3 /data/resources/cmnsd/resources/backup.py yearly /data /backup >/dev/null 2>&1
```
If you made backup.py executable with a shebang (#!/usr/bin/env python3), you can omit python3:
```
0 2 * * 0 /data/resources/cmnsd/resources/backup.py weekly /data /backup >/dev/null 2>&1
```

