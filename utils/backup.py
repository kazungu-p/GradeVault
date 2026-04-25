"""
Backup & restore for GradeVault.
Strategy:
  - Backup  → copy the live SQLite DB into a timestamped .gvbak file
              (which is just a renamed .db — fully portable)
  - Restore → verify the file is a valid GradeVault DB, then swap it in
"""
import sqlite3
from pathlib import Path
from datetime import datetime


DB_PATH  = Path.home() / ".gradevault" / "gradevault.db"
BAK_DIR  = Path.home() / ".gradevault" / "backups"
BAK_EXT  = ".gvbak"


def get_db_path() -> Path:
    return DB_PATH


def backup(dest_path: str = None) -> tuple[bool, str]:
    """
    Copy the live DB to dest_path (or auto-generate a timestamped name).
    Returns (success, message).
    """
    if not DB_PATH.exists():
        return False, "No database found. Nothing to back up."

    if dest_path:
        out = Path(dest_path)
    else:
        BAK_DIR.mkdir(parents=True, exist_ok=True)
        ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = BAK_DIR / f"gradevault_backup_{ts}{BAK_EXT}"

    try:
        # Use SQLite's built-in backup API for a consistent snapshot
        src  = sqlite3.connect(str(DB_PATH))
        dest = sqlite3.connect(str(out))
        src.backup(dest)
        src.close()
        dest.close()
        size = out.stat().st_size
        return True, str(out)
    except Exception as e:
        return False, f"Backup failed: {e}"


def restore(src_path: str) -> tuple[bool, str]:
    """
    Validate and restore a .gvbak file.
    Creates an automatic safety backup of the current DB first.
    Returns (success, message).
    """
    src = Path(src_path)
    if not src.exists():
        return False, "File not found."

    # Validate it's a real GradeVault SQLite database
    ok, msg = validate_backup(src_path)
    if not ok:
        return False, msg

    # Auto-backup current DB before overwriting
    if DB_PATH.exists():
        BAK_DIR.mkdir(parents=True, exist_ok=True)
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        auto_bak = BAK_DIR / f"pre_restore_{ts}{BAK_EXT}"
        try:
            s = sqlite3.connect(str(DB_PATH))
            d = sqlite3.connect(str(auto_bak))
            s.backup(d)
            s.close()
            d.close()
        except Exception:
            pass  # Non-fatal — still proceed with restore

    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        s = sqlite3.connect(src_path)
        d = sqlite3.connect(str(DB_PATH))
        s.backup(d)
        s.close()
        d.close()
        return True, "Restore successful. Please restart GradeVault."
    except Exception as e:
        return False, f"Restore failed: {e}"


def validate_backup(path: str) -> tuple[bool, str]:
    """Check that the file is a valid GradeVault SQLite DB."""
    try:
        conn   = sqlite3.connect(path)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()

        required = {"students", "classes", "subjects",
                    "marks_new", "users", "school_settings"}
        missing  = required - tables
        if missing:
            return False, (f"Invalid backup — missing tables: "
                           f"{', '.join(sorted(missing))}")
        return True, "Valid GradeVault backup."
    except Exception as e:
        return False, f"Cannot read file: {e}"


def list_auto_backups() -> list[dict]:
    """Return list of auto-backups sorted newest first."""
    if not BAK_DIR.exists():
        return []
    baks = []
    for f in sorted(BAK_DIR.glob(f"*{BAK_EXT}"), reverse=True):
        stat = f.stat()
        baks.append({
            "path":     str(f),
            "name":     f.name,
            "size_kb":  round(stat.st_size / 1024, 1),
            "modified": datetime.fromtimestamp(stat.st_mtime
                         ).strftime("%d %b %Y  %H:%M"),
        })
    return baks


def get_db_info() -> dict:
    """Return basic stats about the current database."""
    if not DB_PATH.exists():
        return {}
    try:
        conn = sqlite3.connect(str(DB_PATH))
        students  = conn.execute(
            "SELECT COUNT(*) FROM students").fetchone()[0]
        marks     = conn.execute(
            "SELECT COUNT(*) FROM marks_new").fetchone()[0]
        classes   = conn.execute(
            "SELECT COUNT(*) FROM classes").fetchone()[0]
        conn.close()
        size_kb = round(DB_PATH.stat().st_size / 1024, 1)
        return {
            "path":     str(DB_PATH),
            "size_kb":  size_kb,
            "students": students,
            "marks":    marks,
            "classes":  classes,
        }
    except Exception:
        return {}
