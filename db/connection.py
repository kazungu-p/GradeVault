import sqlite3
from pathlib import Path

DB_DIR = Path.home() / ".gradevault"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "gradevault.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def query(sql: str, params: tuple = ()) -> list:
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def query_one(sql: str, params: tuple = ()):
    with get_connection() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def execute(sql: str, params: tuple = ()) -> int:
    with get_connection() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid


def execute_many(sql: str, params_list: list) -> None:
    with get_connection() as conn:
        conn.executemany(sql, params_list)
        conn.commit()


def execute_script(sql: str) -> None:
    with get_connection() as conn:
        conn.executescript(sql)
        conn.commit()
