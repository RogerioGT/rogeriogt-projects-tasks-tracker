# AGENTS.md — Rogerio Projects & Tasks Tracker

Muse Code reads this file as the project spec. You (Muse) own the code; the
human agent (Hermes) owns planning, review, and deployment. Follow this spec
exactly.

## Product

A full-screen, always-on task board for a **vertical (portrait) monitor**.
Dense, tiny fonts, thin borders, tons of data, color-coded, fast navigation.
Single user now; multi-user + sharing + history later (schema already supports it).

## Tech Stack (non-negotiable)

- Backend: **FastAPI + SQLAlchemy 2.0 + SQLite** (WAL mode). Nothing SQLite-specific
  beyond the connection string + pragmas, so it can swap to Postgres later.
- Frontend: **React + TypeScript + Vite**, **TanStack Virtual** (virtualized lists)
  and **TanStack Table** (sortable/filterable table), **Tailwind CSS**.
- Data fetching: **TanStack Query**.
- Deploy: single Docker container, port 8787, `./data` bind-mounted.

## Data Model (already specified; match these tables/fields)

See `backend/app/models.py`. Tables: `users`, `boards` (nested via parent_id,
kind = section|company|project), `tasks` (status = not_started|in_progress|waiting|done,
priority = high|medium|low|none), `events` (audit history), `board_acl` (sharing).

## Views (build all behind one switcher)

1. **Section Bands** (default): each top-level Section is a colored horizontal band;
   its boards are columns scrolling left/right; tasks scroll down within a column.
2. **Kanban**: columns = status, filtered to one company/project.
3. **List/Table**: sortable/filterable table (title, status, assignee, due, priority, tags, board).
4. **Compact list**: single dense task feed, quick-add on top.

Plus a **Dashboard** tab (charts/reports).

## Visual & Density Rules (critical — Rogerio's portrait monitor)

- Base font **11px**; task rows ~1.35 line-height; **compact is the default**.
- **Thin 1px borders** (subtle), padding 2-4px, column width ~220-260px, gap 4-6px.
- Dark theme default (light optional). Color as accents, not fills.
- Drive everything through CSS variables: `--font-size`, `--row-h`, `--pad`, `--border`.
- Density toggle: compact (default) / cozy.

## Color System

- Sections: Personal Projects=blue(#3b82f6), RC Exteriors=orange(#f97316),
  Clients=green(#22c55e), Ladybug=purple(#a855f7).
- Companies/projects: own color each (palette).
- Status: not_started=gray, in_progress=blue, waiting=amber, done=green.
- Priority: high=red, medium=orange, low=blue, none=gray.

## Behavior Rules

- **New-task input pinned at the top of every column**; new tasks insert at top (position 0 = top).
- Checkbox toggles done; done tasks sink into a collapsed "Completed" section.
- Column header shows color bar, name, task count, "..." menu (rename/recolor/add sub-project/archive/delete).
- Every mutation writes an `events` row (who changed what, for future history).
- Bilingual EN/ES via a translation dictionary; locale persisted per user (default en).

## Conventions

- Backend: Pydantic v2 schemas (`model_config = ConfigDict(from_attributes=True)`),
  routers under `app/routers/`, seed in `app/seed.py`.
- Frontend: TypeScript strict, functional components + hooks, Tailwind utility classes.
- No em-dashes in UI copy. Keep UI text neutral/professional.

## Commands

- Backend run: `uvicorn app.main:app --reload` (from `backend/`).
- Frontend dev: `npm run dev` (from `frontend/`).
- Deploy: `./rebuild-deploy.sh` (Docker Desktop context).
