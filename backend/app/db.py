"""Database engine and session management (SQLAlchemy 2.0 + SQLite).

Deliberately nothing SQLite-specific beyond the connection string and pragmas,
so the future server deployment can swap to Postgres with one line.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

# Default to a data/ dir inside the project so SQLite survives container rebuilds.
DATA_DIR = os.environ.get("DATA_DIR", str(Path(__file__).resolve().parents[2] / "data"))
Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.environ.get(
    "DATABASE_URL", f"sqlite:///{Path(DATA_DIR) / 'tasks.db'}"
)

IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _record):
    if not IS_SQLITE:
        return
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
