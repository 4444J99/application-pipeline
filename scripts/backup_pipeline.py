#!/usr/bin/env python3
"""Backup and restore pipeline YAML files.

Weekly backups protect against accidental corruption. Backups are archived as
dated tar.gz files and committed to git for full audit trail.

Usage:
    python scripts/backup_pipeline.py                  # Create backup
    python scripts/restore_pipeline.py --list          # List available backups
    python scripts/restore_pipeline.py <backup-file>   # Restore from backup
"""

import argparse
import subprocess
import sys
import tarfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import REPO_ROOT


def backup_pipeline() -> str:
    """Create dated backup: pipeline-backup-YYYYMMDD.tar.gz.
    
    Returns backup file path.
    """
    pipeline_dir = REPO_ROOT / "pipeline"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_filename = f"pipeline-backup-{timestamp}.tar.gz"
    backup_path = Path(backup_filename)
    
    try:
        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(pipeline_dir, arcname="pipeline")
        
        print(f"✓ Backup created: {backup_path}")
        print(f"  Size: {backup_path.stat().st_size / 1024 / 1024:.1f} MB")
        
        # Optionally commit to git
        try:
            subprocess.run(
                ["git", "add", str(backup_path)],
                capture_output=True,
                timeout=10
            )
            subprocess.run(
                ["git", "commit", "-m", f"backup: pipeline snapshot {timestamp}"],
                capture_output=True,
                timeout=10
            )
            print(f"  Committed to git")
        except Exception as e:
            print(f"  (git commit failed: {e}, but backup file created)")
        
        return str(backup_path)
    except Exception as e:
        print(f"✗ Backup failed: {e}", file=sys.stderr)
        sys.exit(1)


def list_backups() -> list[Path]:
    """List all available pipeline backups."""
    backups = list(Path(".").glob("pipeline-backup-*.tar.gz"))
    backups.sort(reverse=True)  # Most recent first
    return backups


def restore_pipeline(backup_path: str) -> None:
    """Restore pipeline from backup file.
    
    Creates a git commit documenting the restoration.
    """
    pipeline_dir = REPO_ROOT / "pipeline"
    backup = Path(backup_path)
    
    if not backup.exists():
        print(f"✗ Backup file not found: {backup}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Remove current pipeline
        import shutil
        if pipeline_dir.exists():
            shutil.rmtree(pipeline_dir)
        
        # Extract backup
        with tarfile.open(backup, "r:gz") as tar:
            tar.extractall()
        
        print(f"✓ Restored from: {backup}")
        
        # Commit restoration to git
        try:
            subprocess.run(
                ["git", "add", str(pipeline_dir)],
                capture_output=True,
                timeout=10
            )
            subprocess.run(
                ["git", "commit", "-m", f"restore: pipeline from backup {backup.name}"],
                capture_output=True,
                timeout=10
            )
            print(f"  Committed restoration to git")
        except Exception as e:
            print(f"  (git commit failed: {e}, but restoration completed)")
    
    except Exception as e:
        print(f"✗ Restoration failed: {e}", file=sys.stderr)
        sys.exit(1)


def cleanup_old_backups(keep_days: int = 90) -> None:
    """Remove backups older than keep_days."""
    cutoff = datetime.now().timestamp() - (keep_days * 86400)
    removed = 0
    
    for backup in Path(".").glob("pipeline-backup-*.tar.gz"):
        if backup.stat().st_mtime < cutoff:
            backup.unlink()
            removed += 1
    
    if removed > 0:
        print(f"Cleaned up {removed} backup(s) older than {keep_days} days")


def main():
    parser = argparse.ArgumentParser(description="Pipeline backup and restore")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    subparsers.add_parser("create", help="Create new backup")
    subparsers.add_parser("list", help="List available backups")
    
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup", help="Backup file to restore from")
    
    subparsers.add_parser("cleanup", help="Remove old backups")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "create":
        backup_pipeline()
    elif args.command == "list":
        backups = list_backups()
        if backups:
            print(f"Available backups ({len(backups)} total):")
            for backup in backups:
                size_mb = backup.stat().st_size / 1024 / 1024
                mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                print(f"  {backup.name} ({size_mb:.1f} MB, {mtime})")
        else:
            print("No backups found")
    elif args.command == "restore":
        restore_pipeline(args.backup)
    elif args.command == "cleanup":
        cleanup_old_backups()


if __name__ == "__main__":
    main()
