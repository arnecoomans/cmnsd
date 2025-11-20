#!/usr/bin/env python3
"""
backup.py — version 3.1

Reliable backup script with:
- weekly / monthly / yearly frequencies
- zstd compressed tar creation
- duplicate detection via SHA256
- retention with "never delete last backup"
- email alerts on ANY error
- external config /etc/backup.conf
- dry-run mode
- full logging

Author: Arne Coomans
"""

import os
import sys
import tarfile
import hashlib
import subprocess
import datetime
import shutil
import glob
import traceback
from pathlib import Path

LOGFILE = Path("/var/log/backup.log")
CONFIG_FILE = Path("/etc/backup.conf")


# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
def log(msg):
    LOGFILE.parent.mkdir(parents=True, exist_ok=True)
    with LOGFILE.open("a") as f:
        f.write(msg + "\n")
    print(msg)


# ----------------------------------------------------------------------
# Email support
# ----------------------------------------------------------------------
def load_email():
    """Load ADMIN_EMAIL from /etc/backup.conf"""
    if not CONFIG_FILE.exists():
        return None

    env = {}
    with CONFIG_FILE.open() as f:
        code = compile(f.read(), CONFIG_FILE, "exec")
        exec(code, env, env)

    return env.get("ADMIN_EMAIL")


def send_email(subject, body):
    """Send an email using the system mail command."""
    admin = load_email()
    if not admin:
        log("ADMIN_EMAIL not configured; skipping email alert.")
        return

    # NEW: Log which email address will be used
    log(f"Attempting to send email to: {admin}")

    try:
        p = subprocess.run(
            ["mail", "-s", subject, admin],
            input=body.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if p.returncode != 0:
            log(f"Email send failed: {p.stderr.decode('utf-8')}")
        else:
            log(f"Email successfully sent to: {admin}")
    except Exception as e:
        log(f"Exception while sending email: {e}")


# ----------------------------------------------------------------------
# Error wrapper to ensure email on failure
# ----------------------------------------------------------------------
def fatal_error(message):
    """Log error, send email, and exit."""
    log(f"FATAL: {message}")
    send_email(
        subject=f"BACKUP FAILURE on {os.uname().nodename}",
        body=(
            f"{message}\n\n"
            f"Log file: {LOGFILE}\n"
            f"Timestamp: {datetime.datetime.now()}\n"
        )
    )
    sys.exit(1)


# ----------------------------------------------------------------------
# Utility: hash file
# ----------------------------------------------------------------------
def sha256sum(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ----------------------------------------------------------------------
# Main backup logic
# ----------------------------------------------------------------------
def run_backup(freq, src_dir, dest_root, dry_run=False):
    src = Path(src_dir)
    if not src.exists():
        fatal_error(f"Source directory does not exist: {src}")

    dest_dir = Path(dest_root) / freq
    if not dry_run:
        dest_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.datetime.now()

    if freq == "weekly":
        timestamp = f"{now.year}-{now.isocalendar().week:02d}"
        retention_days = 42
    elif freq == "monthly":
        timestamp = f"{now.year}-{now.month:02d}"
        retention_days = 548
    elif freq == "yearly":
        timestamp = f"{now.year}"
        retention_days = None
    else:
        fatal_error(f"Invalid frequency: {freq}")

    log(f"=== Backup run: {freq} @ {now} ===")
    log(f"Source: {src}")
    log(f"Target: {dest_dir}")
    log(f"Timestamp: {timestamp}")
    log("")

    # Loop over directories in source
    for directory in src.iterdir():
        if not directory.is_dir():
            continue

        name = directory.name
        log(f"--- Processing: {name} ---")

        tmpfile = Path(f"/tmp/{name}_{timestamp}.tar.zst")

        # Create tar.zst archive
        log("Creating archive...")
        try:
            if not dry_run:
                subprocess.check_call([
                    "tar", "-c", "--use-compress-program=zstd",
                    "-f", str(tmpfile),
                    "-C", str(src),
                    name
                ])
            else:
                log(f"[DRY-RUN] Would create tar: {tmpfile}")

        except Exception as e:
            fatal_error(f"Tar creation failed for {name}: {e}")

        # Find previous backups
        pattern = str(dest_dir / f"{name}_*.tar.zst")
        previous = sorted(glob.glob(pattern), reverse=True)
        last_file = previous[0] if previous else None

        # Compare hashes
        if last_file and not dry_run:
            log(f"Last backup: {last_file}")

            try:
                new_hash = sha256sum(tmpfile)
                old_hash = sha256sum(last_file)
            except Exception as e:
                fatal_error(f"Hash comparison failed for {name}: {e}")

            if new_hash == old_hash:
                log("No changes detected — skipping backup.")
                tmpfile.unlink()
                log("")
                continue
            else:
                log("Changes detected — storing new backup.")
        else:
            log("No previous backup — storing new backup.")

        # Save new backup file
        dest_file = dest_dir / f"{name}_{timestamp}.tar.zst"

        if dry_run:
            log(f"[DRY-RUN] Would save backup: {dest_file}")
        else:
            shutil.move(str(tmpfile), str(dest_file))
            log(f"Backup saved: {dest_file}")

        log("")

    # Retention
    if retention_days is not None:
        log(f"Running retention (older than {retention_days} days)...")

        cutoff = now - datetime.timedelta(days=retention_days)

        for directory in src.iterdir():
            if not directory.is_dir():
                continue

            name = directory.name

            files = sorted(glob.glob(str(dest_dir / f"{name}_*.tar.zst")))

            if len(files) <= 1:
                log(f"Skipping retention for {name} — only one backup exists.")
                continue

            for fpath in map(Path, files[:-1]):  # keep newest
                mtime = datetime.datetime.fromtimestamp(fpath.stat().st_mtime)
                if mtime < cutoff:
                    if dry_run:
                        log(f"[DRY-RUN] Would delete {fpath}")
                    else:
                        log(f"Deleting old backup: {fpath}")
                        fpath.unlink()

        log("Retention complete.")

    log(f"Backup for {freq} completed successfully.")
    log("=========================================")


# ----------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------
if __name__ == "__main__":
    try:
        dry = False
        args = sys.argv[1:]

        if args and args[0] == "--dry-run":
            dry = True
            args = args[1:]

        if len(args) != 3:
            print("Usage: backup.py [--dry-run] <weekly|monthly|yearly> <src> <dest>")
            sys.exit(1)

        freq, src, dest = args
        run_backup(freq, src, dest, dry_run=dry)

    except Exception as e:
        tb = traceback.format_exc()
        msg = f"Unhandled exception:\n{e}\n\n{tb}"
        log(msg)
        send_email(
            subject=f"BACKUP CRASH on {os.uname().nodename}",
            body=msg
        )
        sys.exit(1)