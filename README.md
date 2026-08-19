# Rogerio Projects & Tasks Tracker

A full-screen, always-on task board built for a vertical (portrait) monitor.
Dense layout, tiny fonts, thin borders, color-coded hierarchy, fast navigation.
Bilingual English/Spanish. Live at **[tasksmgr.rogeriogt.com](https://tasksmgr.rogeriogt.com)**.

---

## Features

### Board & hierarchy

- **Section bands** as the default view: each top-level section is a colored
  band; boards are columns scrolling left/right; tasks scroll down within a column.
- **Unlimited nesting**: section > company > project > sub-project > ...
- **Drag and drop** columns left/right to reorder or move between sections;
  drag whole section bands up/down to reorder sections.
- **Convert anything at any level**: a task can grow into a project
  (Convert to project), and boards can change level (project <-> company <-> section).
- Custom **color per board** with a palette picker when creating or renaming.

### Tasks

- New-task input pinned at the top of every column; new tasks insert at the top.
- Checkbox toggles done; priority, assignee, due date, description, tags.
- **Custom workflow statuses** (Kanban columns) managed from the admin panel.
- Sort in every filtered view: position, newest, due date, title, priority, status.

### Six views

| View | What it is |
|------|------------|
| Board | Section bands with draggable columns (default) |
| Kanban | Columns = status, filtered to one company/project |
| List | Sortable, filterable table |
| Compact | Dense single task feed with quick-add |
| Dashboard | Stats: totals per status + completion rate |
| History | Full audit trail: who changed what, when |

### Collaboration & security

- **Mandatory login on the server** (`REQUIRE_AUTH=true`); local copies run
  frictionless without auth.
- Users, **teams**, and granular sharing:
  - Share a whole **section/company/project** (inherits down the tree).
  - Share a **single task** or a batch: the recipient sees the hierarchy
    chain but only the shared task(s).
- View vs edit permissions, enforced on every endpoint.
- **Full profile management**: every user edits their own name, email, phone,
  and password; admins edit any member's fields from the People tab.
- **Assignee dropdowns**: task and filter assignees are picked from the people
  the board is actually shared with, instead of free typing.
- **Multiple main boards (workspaces)**: independent board trees you can
  create, rename, switch, and compare from the header or account menu. Each
  has its own sections, columns, and tasks; boards can't be dragged across.
- **Soft delete with 30-day Trash**: deleted boards and tasks are restorable
  from the admin Trash tab, then auto-purged after 30 days.
- Stdlib-only crypto (PBKDF2 password hashing + HMAC-signed tokens), no
  bcrypt/pyjwt build issues in the slim Docker image.
- **Hardening**: login rate limiting (10 attempts / 15 min), strict CORS
  origin list, security headers (nosniff, frame-deny, referrer policy),
  mandatory email validation, admin lockout on deactivation.

### UX

- Dense dark theme by default (light optional), compact/cozy density toggle.
- Bilingual **EN/ES** with a one-click locale switch.
- Responsive: dialogs and header adapt to phone-sized screens.
- Confirmation dialogs on every destructive action.

---

## Tech stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI + SQLAlchemy 2.0 + SQLite (WAL mode) |
| Frontend | React + TypeScript + Vite, TanStack Query, TanStack Virtual |
| Styling | CSS variables, inline styles (dense dark design system) |
| Auth | PBKDF2-HMAC-SHA256 + HMAC tokens (Python stdlib only) |
| Deploy | Single Docker container (multi-stage build) |
| MCP | 50 tools via `mcp` SDK v2, stdlib urllib HTTP client |

SQLite specifics are contained in the connection string + pragmas, so the
database can be swapped to Postgres later with one line.

---

## Repository layout

```
backend/
  app/
    main.py            # FastAPI app, routers, SPA serving
    models.py          # users, boards, tasks, events, ACLs, teams, statuses
    schemas.py         # Pydantic v2 request/response schemas
    access.py          # visibility + permission matrix (ACL inheritance)
    security.py        # PBKDF2 hashing + HMAC token signing
    migrations.py      # idempotent additive column migrations
    seed.py            # initial sections/companies
    deps.py            # auth dependencies (local vs required mode)
    routers/           # boards, tasks, events, auth, sharing, teams, statuses, trash
  tests/test_api.py    # full API regression suite (~90 assertions)
frontend/
  src/
    App.tsx            # top bar, view switcher, auth gate
    api.ts             # typed fetch client
    auth.tsx           # auth context + token persistence
    i18n.tsx           # EN/ES dictionary
    views/             # Board, Kanban, List, Compact, Dashboard, History
    components/        # dialogs, filter bar, admin panel
mcp_server/
  server.py            # MCP server (50 tools)
  README.md            # MCP tool inventory
docker-compose.yml         # local dev (port 8787, no auth)
docker-compose.prod.yml    # production template (REQUIRE_AUTH=true)
rebuild-deploy.sh          # local Docker Desktop rebuild + health check
PLAN.md                    # build plan + locked decisions
```

---

## Getting started (local development)

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --reload --port 8787
```

No auth required locally: requests fall back to a local pseudo-user.
API docs at http://localhost:8787/docs.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to `http://localhost:8787`.

### 3. Or run the whole thing in Docker

```bash
./rebuild-deploy.sh
```

Builds the image (frontend compiled inside the multi-stage Dockerfile),
starts the container, waits for the health check on port 8787.
Data persists in the bind-mounted `./data` directory.

---

## Tests

The backend suite covers auth, sharing/visibility matrix, team lifecycle,
custom statuses, task conversion, sorting, drag-drop move/cycle guards,
soft delete + trash restore + purge, and the security regression checks.

```bash
cd backend
rm -rf /tmp/tt-test-data
REQUIRE_AUTH=true \
ADMIN_EMAIL=admin@rogeriogt.com \
ADMIN_PASSWORD=test1234 \
DATA_DIR=/tmp/tt-test-data \
.venv/bin/python tests/test_api.py
```

---

## Production deployment

Production runs on a VPS (195.35.8.46) behind Caddy with auto-HTTPS.

```bash
# On the VPS:
cd /opt/tasks-tracker
git pull --ff-only
docker compose up -d --build
```

`docker-compose.prod.yml` is copied to `docker-compose.override.yml` on the
server with real secrets. The container binds `127.0.0.1:8790:8787` (localhost
only); Caddy reverse-proxies https://tasksmgr.rogeriogt.com to it.

### Environment variables (production)

| Variable | Purpose |
|----------|---------|
| `REQUIRE_AUTH` | `true` = mandatory login (registration closed, admin bootstrapped) |
| `ADMIN_EMAIL` | Bootstrap admin account email (promoted to admin on every startup) |
| `ADMIN_PASSWORD` | Bootstrap admin password (used on first creation) |
| `SECRET_KEY` | HMAC token signing secret |
| `DATA_DIR` | SQLite data directory (persisted via volume) |

---

## MCP server: drive the board from chat

The MCP server exposes **50 tools** covering the entire API, so any MCP client
(Hermes, VS Code Copilot, Cline, Claude Desktop, etc.) can drive the tracker
from chat: "add task X to eyegenerate.com", "move 5bell.com under Personal
Projects", "restore the deleted project", "mark task Y completed", etc.

The server is a **stdio** Python program: it talks to the backend REST API over
HTTP. Two environment variables control it:

| Variable | Purpose |
|----------|---------|
| `TASKS_API_URL` | Backend base URL (default `http://localhost:8787`) |
| `TASKS_API_TOKEN` | Bearer token for `REQUIRE_AUTH=true` servers (from `POST /api/auth/login`). Omit for local dev (no auth). |

The command is always the same; only the `env` changes per target:

```bash
/path/to/mcp_server/.venv/bin/python /path/to/mcp_server/server.py
```

(On this machine the venv lives at
`~/Documents/rogeriogt-projects-tasks-tracker/mcp_server/.venv`.)

### Step 0 — get an API token (required for the live server)

```bash
curl -s -X POST https://tasksmgr.rogeriogt.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"YOUR_EMAIL","password":"YOUR_PASSWORD"}'
```

The `token` field in the response is your bearer token. **Tokens expire after
30 days**, so re-run this when a client starts returning auth errors. For local
development (backend running on `localhost:8787`) no token is needed at all.

### Step 1 — create a user for each person

Admin creates users in the web app (⚙ Settings → People → add user) or via MCP
`add_user`. Each person then logs in with their own email/password, gets their
own API token (Step 0), and connects their own client. Share the boards/sections
they should see (Share button on any board, or MCP `share_board`), and their
assignee dropdown automatically lists the people they share with.

### Connect to Hermes

```bash
hermes mcp add tasks_tracker \
  --command /path/to/mcp_server/.venv/bin/python \
  --args /path/to/mcp_server/server.py
```

Set `TASKS_API_URL` and `TASKS_API_TOKEN` in the environment where Hermes runs
for the live server (see `~/.hermes` env files), then verify with
`hermes mcp test tasks_tracker`.

### Connect to VS Code (Copilot Chat)

VS Code reads MCP servers from two places:

1. **User-level (applies to every workspace):** `~/.config/Code/User/mcp.json`
2. **Workspace-level (one repo):** `.vscode/mcp.json` in the repo root

Add this entry (adjust the absolute paths to the machine):

```json
{
  "servers": {
    "tasks-tracker": {
      "type": "stdio",
      "command": "/home/leyo/Documents/rogeriogt-projects-tasks-tracker/mcp_server/.venv/bin/python",
      "args": [
        "/home/leyo/Documents/rogeriogt-projects-tasks-tracker/mcp_server/server.py"
      ],
      "env": {
        "TASKS_API_URL": "https://tasksmgr.rogeriogt.com",
        "TASKS_API_TOKEN": "${input:tasks_tracker_token}"
      }
    }
  },
  "inputs": [
    {
      "id": "tasks_tracker_token",
      "type": "promptString",
      "description": "Tasks Tracker API token (from POST /api/auth/login)",
      "password": true
    }
  ]
}
```

The `${input:tasks_tracker_token}` + `inputs` pair makes VS Code prompt for the
token once (masked, stored securely) instead of hard-coding it. Alternatively
paste the token straight into `TASKS_API_TOKEN` if you prefer. Then in VS Code:
open Copilot Chat → Configure Tools → tick "tasks-tracker" → Start.

A ready-to-copy template also lives in the repo at `.vscode/mcp.example.json`
(the live `.vscode/mcp.json` is gitignored so tokens never leak to GitHub).

### Connect to other clients (Cline, Claude Desktop, n8n, etc.)

The same stdio command + env works everywhere. For a GUI that only asks for
command/args/env: command = the venv python, args = `server.py` path, env =
`TASKS_API_URL` + `TASKS_API_TOKEN`. For a system that runs the server as a
child process, set both env vars before spawning it.

Full tool inventory: see [mcp_server/README.md](mcp_server/README.md).

---

## API overview

All endpoints live under `/api`. Auth via `Authorization: Bearer <token>`.

| Area | Endpoints |
|------|-----------|
| Workspaces | `GET/POST /workspaces`, `PATCH/DELETE /workspaces/{id}`, `POST /workspaces/{id}/restore`, `DELETE /workspaces/trash/{id}` |
| Boards | `GET/POST /boards`, `PATCH/DELETE /boards/{id}`, `GET /boards/tree`, `POST /boards/{id}/move`, `POST /boards/{id}/convert`, `GET /boards/{id}/assignees` |
| Tasks | `GET/POST /tasks`, `PATCH/DELETE /tasks/{id}`, `POST /tasks/{id}/complete|move|convert`, `GET /tasks/stats/summary` |
| Sharing | `GET/POST/DELETE /boards/{id}/acl`, `GET/POST/DELETE /tasks/{id}/acl`, `POST /tasks/share` (batch) |
| Auth | `POST /auth/login`, `GET /auth/me`, `PATCH /auth/me` (own profile), `GET /auth/users`, `POST /auth/change-password` |
| Admin | `POST/PATCH /auth/users` (full member edit incl. phone/password), `GET/POST/PATCH/DELETE /teams` (+ members), `POST/PATCH/DELETE /statuses` |
| Trash | `GET /trash`, `POST /trash/{boards,tasks}/{id}/restore`, `DELETE /trash/{boards,tasks}/{id}` |
| History | `GET /events` (filters: entity_type, action, limit) |

OpenAPI docs: `/docs` on any running instance.

---

## Version history

| Version | Highlights |
|---------|------------|
| v1.0 | Board/Kanban/List/Compact views, bilingual, drag-drop, MCP basics |
| v1.1 | Task -> project conversion, sorting in all filtered views |
| v1.2 | History with user names, drag-drop sections, delete warnings, mobile view |
| v1.3 | Hierarchy kind conversion, soft delete with 30-day Trash |
| v1.4 | Complete MCP coverage (42 tools) |
| v1.5 | Section management menu, fixed vertical section drag-drop |
| v1.6 | Security/logic audit: sharing permissions, auth on user list, purge crash fix, PATCH hardening, trashed-entity guards |
| v1.7 | Multiple main boards (workspaces), assignee dropdowns from shared users |
| v1.8 | Full profile management (name/email/phone/password), login rate limiting, security headers, stricter CORS |

---

## License

Private project by Rogerio Martinez. Not open for redistribution.
