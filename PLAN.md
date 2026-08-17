# Rogerio's Projects & Tasks Tracker — Build Plan

> **Status:** v0.2 — decisions locked (see §1). Building in phases.
> **Author:** Hermes (vibecoding profile) with Rogerio.
> **Coding engine:** `muse` (Muse Code CLI, Meta OAuth, model `muse-spark-1.2-contributor`).

---

## 1. Locked Decisions (confirmed by Rogerio)

| # | Decision | Choice |
|---|---|---|
| 1 | Board layout | "Section bands" board as default, PLUS 3-4 view options to test |
| 2 | UI language | **Bilingual** English + Spanish (locale toggle) |
| 3 | Access (now) | **localhost only** (single user, no login) |
| 3b | Access (future) | Deploy to a subdomain with **multi-user**, share projects, edit/view ACL |
| 4 | Hierarchy | **Flexible unlimited nesting**, can insert new level anywhere/any depth |
| 5 | Tech stack | **FastAPI + SQLite + React (TypeScript)** |
| 6 | Seed data | Pre-load wireframe sections + companies |

## 2. Vision

A full-screen, always-on task board on Rogerio's vertical (portrait) monitor.
Dense, tiny fonts, thin borders, tons of data, color-coded, fast navigation.

- Scroll **down** for a company's tasks; **left/right** for more projects/companies.
- New-task input **pinned at the top** of every column (most recent on top).
- Checkbox to mark done; sort/filter by status, priority, assignee, due date.
- Dashboard (charts) + MCP server to drive the app from Hermes chat.

## 3. Data Model (future-proofed for multi-user + sharing + history)

Unified **boards + tasks**. "Board" is any container (Section, Company, Project,
Sub-project); boards nest via `parent_id` = unlimited hierarchy. Everything is
designed for a single user now, multi-user later without a rewrite.

### `users` (future auth)
id, email, name, locale, is_active, created_at

### `boards`
id · parent_id (null = top-level Section) · name · kind (section/company/project) ·
color · sort_order · created_by · created_at · updated_at

### `tasks`
id · board_id · title · description · status (not_started/in_progress/waiting/done) ·
priority (high/medium/low/none) · assignee · due_date · tags (json) · position ·
completed_at · created_by · updated_by · created_at · updated_at

### `events` (audit history — "who made what change")
id · entity_type (task/board) · entity_id · user_id · action (create/update/complete/move/delete) ·
field · old_value · new_value · created_at

### `board_acl` (sharing — "choose what to share, view vs edit")
id · board_id · user_id · permission (view/edit) · created_at.
Access **inherits down the tree**: share a Company and all its Projects/Tasks are
shared; share a single Project and only that subtree is shared.

## 4. Color System

- **Sections:** Personal Projects = blue · RC Exteriors = orange · Clients = green · Ladybug = purple.
- **Companies/Projects:** own color each (palette auto-assign or manual pick).
- **Status:** Not started = gray · In progress = blue · Waiting = amber · Done = green.
- **Priority:** High = red · Medium = orange · Low = blue · None = gray.

## 5. Views (4 options, switchable — Rogerio tests and picks favorites)

1. **Section Bands** (default) — each Section is a colored horizontal band; columns
   scroll left/right, tasks scroll down. See everything at once.
2. **Kanban** — columns = status (To Do / In Progress / Waiting / Done), cards move
   across; filtered to one company/project at a time.
3. **List / Table** — Notion-style sortable/filterable table (title, status,
   assignee, due, priority, tags, board). Best for sorting/filtering everything.
4. **Compact list** — single-column dense task feed with quick-add on top, minimal
   chrome, for a narrow/phone-ish window.

Plus a **Dashboard** (separate tab): charts/reports.

## 6. Density & Visual Spec (the portrait monitor)

- **Base font 11px**, task rows ~1.35 line-height, **compact** is default.
- **Thin 1px borders** (subtle, e.g. #2a2a2a on dark), minimal padding (2-4px).
- Column width ~220-260px, gap ~4-6px. Density toggle: compact (default) / cozy.
- CSS variables drive everything (`--font-size`, `--row-h`, `--pad`, `--border`).
- Dark theme default (matches Rogerio's other tools), light optional.
- High contrast but not harsh; color used as accents, not fills.

## 7. i18n

Bilingual EN/ES via a translation dictionary in the frontend (no per-string
duplication). Locale persisted per user (default `en`). Toggle in top bar.

## 8. Tech Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI + SQLAlchemy 2.0 + SQLite (WAL mode) |
| Frontend | React + TypeScript + Vite + TanStack Virtual/Table + Tailwind |
| Data | TanStack Query (caching, optimistic updates) |
| MCP | FastMCP stdio server (talks to REST API) |
| Deploy | Docker multi-stage, single container, port 8787 |

SQLite now via SQLAlchemy so the future server deployment can swap to Postgres
with a config change (multi-user, concurrent writes).

## 9. Repo Layout

```
rogeriogt-projects-tasks-tracker/
├── backend/            # FastAPI + SQLite
│   ├── app/ (main.py, db.py, models.py, schemas.py, seed.py, routers/)
│   └── requirements.txt
├── frontend/           # React + TS + Vite
├── mcp/                # FastMCP server
├── data/               # tasks.db (bind-mounted, survives rebuilds)
├── docker-compose.yml
├── Dockerfile
├── rebuild-deploy.sh
└── PLAN.md
```

## 10. Deployment

- **Now:** Docker Desktop (`desktop-linux`), `http://localhost:8787`, `./data`
  bind-mounted. `rebuild-deploy.sh` = use context → build → up -d → health check → print URL.
- **Future:** subdomain on a server, Postgres, users + ACL + audit history.

## 11. Roadmap

- **Phase 0 — Scaffold:** structure, Dockerfile, compose, rebuild-deploy.sh, schema, seed.
- **Phase 1 — Backend:** CRUD for boards + tasks, sort/filter/search, complete/move, health.
- **Phase 2 — Board view (Section Bands):** columns, pinned new-task, checkbox, drag.
- **Phase 3 — Other views:** Kanban, List/Table, Compact.
- **Phase 4 — Polish:** color system, density, dark/light, i18n EN/ES, tiny-font tuning.
- **Phase 5 — Dashboard:** charts/reports.
- **Phase 6 — MCP:** FastMCP server + Hermes registration.
- **Phase 7 — Real data + test:** load real tasks, verify full-screen on portrait monitor.

## 12. Recommendations (from Hermes)

1. **Schema now, users later.** Build `users`, `events`, `board_acl` tables from day
   one (empty/self-populated) so the future multi-user/sharing/history feature is
   a UI change, not a migration.
2. **SQLite → Postgres via SQLAlchemy.** Write nothing SQLite-specific; swap the
   connection string when you go to the server.
3. **Optimistic UI + audit.** Every mutation writes an `events` row; the UI updates
   instantly then reconciles. This gives you "who changed what" for free.
4. **Sharing = ACL on a board subtree.** Checkboxes in a "Share" dialog map to
   `board_acl` rows with view/edit. Inheritance handles "share whole company" vs
   "share one project".
5. **Dense first.** Default compact; offer cozy. 11px base, 1px borders.
6. **Build views behind one switcher** so you can A/B them without redeploying.
7. **MCP last.** Get the REST API solid first; MCP is a thin wrapper over it.

## 13. Immediate Next Steps (this build)

1. Scaffold repo + Docker + rebuild-deploy.sh (Phase 0).
2. Backend API working end-to-end (Phase 1).
3. Verify health + a few API calls against the real container.
4. Then frontend Section Bands (Phase 2).
