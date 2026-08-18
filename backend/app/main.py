"""FastAPI application entrypoint."""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import Base, SessionLocal, engine
from .routers import boards, tasks, events, auth, sharing, teams, statuses, trash, workspaces
from .seed import seed
from .migrations import run_migrations
from .routers.auth import bootstrap_admin
from .routers.statuses import seed_statuses
from .routers.trash import purge_expired
from .routers.workspaces import backfill_boards, purge_expired_workspaces

Base.metadata.create_all(bind=engine)
run_migrations()

app = FastAPI(title="Rogerio Projects & Tasks Tracker", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # localhost single-user; tighten on server deploy
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(boards.router)
app.include_router(tasks.router)
app.include_router(events.router)
app.include_router(auth.router)
app.include_router(sharing.router)
app.include_router(teams.router)
app.include_router(statuses.router)
app.include_router(trash.router)
app.include_router(workspaces.router)

# Serve the built frontend if present (SPA). Falls back to API root otherwise.
_FRONTEND_DIR = Path(os.environ.get("FRONTEND_DIR", "/app/frontend/dist"))
if _FRONTEND_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIR / "assets"), name="assets")
    _public = _FRONTEND_DIR  # favicon.svg and other top-level public files
    if (_public / "favicon.svg").is_file():

        @app.get("/favicon.svg", include_in_schema=False)
        def favicon():
            return FileResponse(_public / "favicon.svg")

        @app.get("/favicon.ico", include_in_schema=False)
        def favicon_ico():
            # some browsers still probe favicon.ico — serve the same icon
            return FileResponse(_public / "favicon.svg")


@app.on_event("startup")
def _seed_on_startup():
    db = SessionLocal()
    try:
        seed(db)
        seed_statuses(db)
        bootstrap_admin(db)
        backfill_boards(db)
        purge_expired()
        purge_expired_workspaces()
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    index = _FRONTEND_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {"app": "Rogerio Projects & Tasks Tracker", "docs": "/docs", "api": "/api"}
