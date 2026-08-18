# Rogerio's Projects & Tasks Tracker — Build Plan

> **Status:** v1.6 — v1.5 + full security/logic audit (sharing permissions, auth on user list, purge crash fix, PATCH hardening, trashed-entity guards, auto-color, MCP reorder fix).
> **Author:** Hermes (vibecoding profile) with Rogerio.
> **Coding engine:** Hermes direct (backend) + React/TS frontend. MCP SDK v2.

---

## 1. Locked Decisions (confirmed by Rogerio)

| # | Decision | Choice |
|---|---|---|
| 1 | Board layout | "Section bands" board as default, plus Kanban, List, Compact, Dashboard, History |
| 2 | UI language | **Bilingual** English + Spanish (locale toggle) |
| 3 | Access | **Mandatory login on the server** (REQUIRE_AUTH=true); local copy stays frictionless |
| 4 | Hierarchy | **Flexible unlimited nesting** (section > company > project > ...) |
| 5 | Tech stack | **FastAPI + SQLite + React (TypeScript)**, Docker deploy |
| 6 | Seed data | Pre-load wireframe sections + companies |
| 7 | Crypto | Stdlib only (PBKDF2 + HMAC tokens) — no bcrypt/pyjwt in the image |

## 2. Vision

A full-screen, always-on task board on Rogerio's vertical (portrait) monitor,
reachable anywhere at https://tasksmgr.rogeriogt.com. Dense, tiny fonts, thin
borders, tons of data, color-coded, fast navigation.

- Scroll **down** for a company's tasks; **left/right** for more projects/companies.
- New-task input **pinned at the top** of every column (most recent on top).
- Checkbox to mark done; filter by status, priority, assignee, due date.
- Dashboard (stats) + History (audit trail) + MCP server to drive the app from Hermes chat.
- Multi-user: teams, granular sharing (task → project → company → section), view/edit.

## 3. Actual State (what is built and shipped)

### Backend (FastAPI + SQLAlchemy 2.0 + SQLite, WAL)
- `users` (id, email, name, password_hash, locale, is_active, created_at)
- `boards` (parent_id nesting, kind=section|company|project, color, sort_order, created_by)
- `tasks` (status not_started|in_progress|waiting|done, priority high|medium|low|none,
  assignee, due_date, tags JSON, position, completed_at, created_by/updated_by)
- `events` (audit history: entity, action, field, old/new value, user, time)
- `board_acl` (board subtree sharing, view|edit, inherits down the tree)
- Routers: boards (CRUD + tree), tasks (CRUD + filters + complete + move + stats),
  events (list), auth (register/login/me/users/required + admin bootstrap), sharing (board ACL)
- `migrations.py` — idempotent additive-column migrations (SQLite survives code updates)
- `deps.py` — `get_current_user`: Bearer token wins; local pseudo-user in local mode;
  401 when REQUIRE_AUTH=true
- `security.py` — PBKDF2 password hashing + HMAC-signed tokens (stdlib only)

### Frontend (React + TS + Vite + TanStack Query/Virtual)
- Views: **Board** (section bands), **Kanban**, **List**, **Compact**, **Dashboard**, **History**
- 11px dense dark theme, density toggle (compact/cozy), dark/light toggle, EN/ES
- Board "..." menu: rename, recolor, add sub-board, **share**, delete
- Account button (top right): login/logout, register (only in local mode)
- Full-screen login gate when the server reports `auth_required=true`
- Token auto-attached to every API call from `req()` helper

### MCP server (`mcp_server/server.py`, mcp SDK v2, stdlib urllib)
9 tools: `list_boards`, `list_tasks`, `create_task`, `toggle_complete`, `update_task`,
`move_task`, `delete_task`, `add_board`, `dashboard_stats`. Board name resolution
(exact → partial match). Registered in Hermes as `tasks_tracker` (mcp_tasks_tracker_*).

### Deploy
- **Local:** Docker Desktop, `http://localhost:8787`, `./data` bind-mounted, no login.
- **Prod:** https://tasksmgr.rogeriogt.com → VPS 195.35.8.46, `/opt/tasks-tracker`,
  Docker on `127.0.0.1:8790` (8787 was held by a stale docker-proxy), Caddy
  reverse-proxy + auto-HTTPS, REQUIRE_AUTH=true, admin bootstrapped from env.
- Admin: admin@rogeriogt.com (password stored in env; changeable via settings later).
- Repo: github.com/RogerioGT/rogeriogt-projects-tasks-tracker (main).

## 4. Enhancements (next phases — Rogerio's requests, 2026-08-18)

### Phase 10 — Teams & Roles (admin)
- New tables: `teams` (id, name, created_by, created_at), `team_members`
  (team_id, user_id, role: member|admin).
- Admin UI: create team, add/remove members, rename, delete.
- Admin user management: list users, create user (admin sets password), activate/deactivate.
- Admin = a user with `is_admin` flag (add column via migrations.py).

### Phase 11 — Granular Sharing
Today sharing = board subtree (view|edit) only. Extend to every level:
- **Task-level ACL** — new `task_acl` table (task_id, user_id|team_id, view|edit).
  Share ONE task or a selected list of tasks (batch endpoint).
- **Team sharing** — `board_acl`/`task_acl` accept a team_id as alternative to user_id.
- Share dialog update: pick person OR team; pick scope (task(s)/project/company/section).
- Enforcement: every list/create/update/delete endpoint resolves effective permission
  (explicit ACL or inherited from ancestor board ACL).

### Phase 12 — Filters for Kanban / List / Compact (+ Board)
- Cascading filter bar: **Company select** → **Project select** (only projects under
  that company) → status / priority / assignee / due filters. Every select has an
  **All** option (default).
- Backend: add company-scoped query params (board subtree ids), plus assignee/status/
  priority already supported; add due-date range.
- Board view: quick section/company jump (same filter bar, filters columns).

### Phase 13 — MCP Admin Tools
- Add: `update_board`, `delete_board`, `list_users`, `add_user`, `list_teams`,
  `add_team`, `add_team_member`, `share_board`/`unshare_board`, `share_task(s)`.
- Auth support: MCP reads `TASKS_API_TOKEN` env and sends Bearer header, so it can
  drive the production server from chat (default remains localhost:8787).

### Phase 14 — Admin Settings UI
- Settings dialog (gear icon): change own password, manage users, manage teams,
  app title, locale default. Backed by new `/api/settings` + admin endpoints.

## 5. Data Model (future-proofed for multi-user + sharing + history)

Unified **boards + tasks**. "Board" is any container (Section, Company, Project,
Sub-project); boards nest via `parent_id` = unlimited hierarchy.

- `users` — + `is_admin` (Phase 10)
- `teams`, `team_members` (Phase 10)
- `boards`, `tasks`, `events`, `board_acl` — shipped
- `task_acl` (Phase 11)

Access **inherits down the tree**: share a Company and all its Projects/Tasks are
shared; share a single Project and only that subtree is shared; share a single Task
and only that task is visible.

## 6. Color System

- **Sections:** Personal Projects = blue · RC Exteriors = orange · Clients = green · Ladybug = purple.
- **Companies/Projects:** own color each (palette auto-assign or manual pick).
- **Status:** Not started = gray · In progress = blue · Waiting = amber · Done = green.
- **Priority:** High = red · Medium = orange · Low = blue · None = gray.

## 7. Views (6 behind one switcher)

1. **Board / Section Bands** (default) — each Section is a colored horizontal band;
   columns scroll left/right, tasks scroll down. Phase 12 adds the filter bar.
2. **Kanban** — columns = status; Phase 12 adds company/project cascading filters.
3. **List / Table** — sortable/filterable table; Phase 12 adds the same filters.
4. **Compact list** — dense single-column feed, quick-add on top.
5. **Dashboard** — total/done/waiting/in-progress cards, completion rate, per-status,
   per-priority, per-section bars.
6. **History** — audit trail (action, entity, value, relative time), filter all/tasks/boards.

## 8. Density & Visual Spec (the portrait monitor)

- **Base font 11px**, task rows ~1.35 line-height, **compact** is default.
- **Thin 1px borders**, minimal padding (2-4px). Column width ~220-260px, gap 4-6px.
- Density toggle: compact (default) / cozy. Dark default, light optional.
- CSS variables drive everything (`--font-size`, `--row-h`, `--pad`, `--border`).

## 9. i18n

Bilingual EN/ES via a translation dictionary in the frontend. Locale persisted per
user (default `en`). Toggle in top bar.

## 10. Tech Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI + SQLAlchemy 2.0 + SQLite (WAL mode) |
| Frontend | React + TypeScript + Vite + TanStack Virtual/Query |
| Auth | PBKDF2 + HMAC tokens (stdlib) |
| MCP | mcp SDK v2 (mcpserver), stdlib urllib |
| Deploy | Docker multi-stage, single container |

SQLite now via SQLAlchemy so the future server deployment can swap to Postgres
with a config change (multi-user, concurrent writes).

## 11. Repo Layout

```
rogeriogt-projects-tasks-tracker/
├── backend/            # FastAPI + SQLite (app/: main, db, models, schemas, seed,
│                       #   security, deps, migrations, routers/)
├── frontend/           # React + TS + Vite (src/: views/, components/, api, auth, i18n)
├── mcp_server/         # MCP server (server.py, README.md, own .venv)
├── data/               # tasks.db (bind-mounted, survives rebuilds)
├── docker-compose.yml / docker-compose.prod.yml
├── Dockerfile
├── rebuild-deploy.sh
└── PLAN.md
```

## 12. Deployment

- **Local:** Docker Desktop (`desktop-linux`), `http://localhost:8787`, no login.
- **Prod:** https://tasksmgr.rogeriogt.com — `/opt/tasks-tracker` on 195.35.8.46,
  `docker-compose.override.yml` (127.0.0.1:8790:8787, REQUIRE_AUTH, ADMIN_*, SECRET_KEY),
  Caddy `reverse_proxy 127.0.0.1:8790`, auto-HTTPS. Deploy flow: git push → VPS
  `git pull --ff-only` → `docker compose up -d --build`.
- Postgres + heavier scaling only when needed.

## 13. Roadmap (actual)

- [x] **Phase 0 — Scaffold:** structure, Dockerfile, compose, rebuild-deploy.sh, schema, seed.
- [x] **Phase 1 — Backend:** CRUD for boards + tasks, sort/filter/search, complete/move, health.
- [x] **Phase 2 — Board view (Section Bands):** columns, pinned new-task, checkbox.
- [x] **Phase 3 — Other views:** Kanban, List/Table, Compact.
- [x] **Phase 4 — Polish:** color system, density, dark/light, i18n EN/ES, 11px tuning.
- [x] **Phase 5 — Dashboard:** stats cards + bars.
- [x] **Phase 6 — MCP:** stdio server (9 tools) + Hermes registration.
- [x] **Phase 7 — History view:** events endpoint + HistoryView tab with filters.
- [x] **Phase 8 — Multi-user + sharing:** auth (register/login/me), board ACL share, migrations.
- [x] **Phase 9 — Mandatory login + deploy:** REQUIRE_AUTH mode, admin bootstrap, login gate,
  deployed to https://tasksmgr.rogeriogt.com (Caddy, port 8790). Token-fix for all requests.
- [ ] **Phase 10 — Teams & Roles:** teams/team_members tables, admin user management, is_admin.
- [ ] **Phase 11 — Granular Sharing:** task_acl, team targets, share scope (task(s)/project/company/section), enforcement.
- [ ] **Phase 12 — Filters:** cascading company→project filters + status/priority/assignee/due, All option, on Kanban/List/Compact/Board.
- [ ] **Phase 13 — MCP admin tools:** board edit/delete, users/teams, sharing tools, token auth for prod.
- [ ] **Phase 14 — Admin Settings UI:** change password, manage users/teams, app settings.

## 14. Immediate Next Steps

1. Phase 10 (teams + admin user management) — schema + endpoints first, then admin UI.
2. Phase 11 (granular sharing) right after, since the share dialog depends on teams.
3. Phase 12 (filters) can proceed in parallel — pure frontend + small backend additions.
4. Phase 13 (MCP admin) once the REST endpoints from 10/11 exist.
