"""FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, SessionLocal, engine
from .routers import boards, tasks
from .seed import seed

Base.metadata.create_all(bind=engine)

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


@app.on_event("startup")
def _seed_on_startup():
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"app": "Rogerio Projects & Tasks Tracker", "docs": "/docs", "api": "/api"}
