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
