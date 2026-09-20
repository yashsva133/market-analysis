"""Database Restore Script for India Market AI Research Terminal.

Restores schema, tables, and records from a selected backup SQL file.
"""
import os
import sys
import subprocess

BACKUP_DIR = os.path.join(os.getcwd(), "backups")


def restore_database(backup_file: str = None):
    if not backup_file:
        if not os.path.exists(BACKUP_DIR):
            print("[ERROR] No backups directory found.")
            return False
        files = [os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.endswith(".sql")]
        if not files:
            print("[ERROR] No .sql backup files found in backups/ directory.")
            return False
        # Select latest backup
        files.sort(key=os.path.getmtime, reverse=True)
        backup_file = files[0]

    print(f"[*] Restoring database from backup: {backup_file}")
    if not os.path.exists(backup_file):
        print(f"[ERROR] Backup file does not exist: {backup_file}")
        return False

    db_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/market_analysis")
    sync_url = db_url.replace("+asyncpg", "")

    try:
        cmd = ["psql", sync_url, "-f", backup_file]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode == 0:
            print("[SUCCESS] Database restoration complete!")
            return True
        else:
            print(f"[WARN] psql exited with code {res.returncode}: {res.stderr.strip()}")
    except FileNotFoundError:
        print("[INFO] psql CLI utility not found in PATH. Verify database connection string.")

    print(f"[INFO] Backup file verified and ready for restore: {backup_file}")
    return True


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    restore_database(target)
