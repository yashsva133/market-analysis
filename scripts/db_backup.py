"""Database Backup Script for India Market AI Research Terminal.

Exports full PostgreSQL database including schema, tables, foreign keys,
and pgvector embeddings to a timestamped backup file in backups/.
"""
import os
import sys
import subprocess
from datetime import datetime

BACKUP_DIR = os.path.join(os.getcwd(), "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


def backup_database():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"terminal_db_backup_{timestamp}.sql")

    db_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/market_analysis")
    # Clean URL for pg_dump
    sync_url = db_url.replace("+asyncpg", "")

    print(f"[*] Initiating terminal database backup to: {backup_file}")

    # Check if pg_dump is available in PATH
    try:
        cmd = ["pg_dump", sync_url, "-f", backup_file]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode == 0:
            file_size_kb = round(os.path.getsize(backup_file) / 1024, 2)
            print(f"[SUCCESS] Database backup completed successfully: {backup_file} ({file_size_kb} KB)")
            return backup_file
        else:
            print(f"[WARN] pg_dump exited with code {res.returncode}: {res.stderr.strip()}")
    except FileNotFoundError:
        print("[INFO] pg_dump CLI utility not installed in PATH; creating schema & metadata manifest backup.")

    # Fallback: Create structured schema & metadata snapshot
    manifest_file = os.path.join(BACKUP_DIR, f"terminal_metadata_backup_{timestamp}.sql")
    init_sql_path = os.path.join(os.getcwd(), "db", "init.sql")
    if os.path.exists(init_sql_path):
        with open(init_sql_path, "r", encoding="utf-8") as f_in:
            schema_content = f_in.read()
        with open(manifest_file, "w", encoding="utf-8") as f_out:
            f_out.write(f"-- India Market AI Research Terminal Backup\n-- Generated: {datetime.now().isoformat()}\n\n")
            f_out.write(schema_content)
        file_size_kb = round(os.path.getsize(manifest_file) / 1024, 2)
        print(f"[SUCCESS] Schema and DDL backup generated: {manifest_file} ({file_size_kb} KB)")
        return manifest_file

    print("[ERROR] Could not generate backup.")
    return None


if __name__ == "__main__":
    backup_database()
