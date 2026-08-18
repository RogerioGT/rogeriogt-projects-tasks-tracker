"""Lightweight schema migrations for SQLite.

create_all() only creates tables that don't exist; it never adds columns to an
existing table. This runs after create_all and applies additive column changes
idempotently so a live SQLite file survives code updates without a wipe.
"""
from sqlalchemy import text

from .db import IS_SQLITE, engine

# (table, column, ddl) — additive, idempotent, ordered.
_MIGRATIONS = [
    ("users", "password_hash", "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"),
    ("users", "is_admin", "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0"),
    ("board_acl", "team_id", "ALTER TABLE board_acl ADD COLUMN team_id VARCHAR(36)"),
    ("boards", "deleted_at", "ALTER TABLE boards ADD COLUMN deleted_at DATETIME"),
    ("tasks", "deleted_at", "ALTER TABLE tasks ADD COLUMN deleted_at DATETIME"),
]


def _column_names(table: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def run_migrations() -> None:
    if not IS_SQLITE:
        return
    with engine.begin() as conn:
        for table, column, ddl in _MIGRATIONS:
            if column not in _column_names(table):
                conn.execute(text(ddl))
