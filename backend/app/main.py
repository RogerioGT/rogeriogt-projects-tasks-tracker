"""FastAPI application entrypoint."""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import Base, SessionLocal, engine
from .routers import boards, tasks, events, auth, sharing, teams
from .seed import seed
from .migrations import run_migrations
from .routers.auth import bootstrap_admin

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

# Serve the built frontend if present (SPA). Falls back to API root otherwise.
_FRONTEND_DIR = Path(os.environ.get("FRONTEND_DIR", "/app/frontend/dist"))
if _FRONTEND_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIR / "assets"), name="assets")


@app.on_event("startup")
def _seed_on_startup():
    db = SessionLocal()
    try:
        seed(db)
        bootstrap_admin(db)
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
