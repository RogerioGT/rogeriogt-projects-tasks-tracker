# MCP Server — Tasks Tracker

Lets Hermes drive the task board from chat. Type "add task X to eyegenerate.com"
and the MCP tools resolve the board name and create the task.

## What it exposes (42 tools)

| Area | Tools |
|------|-------|
| Boards | `list_boards`, `add_board`, `update_board`, `move_board`, `convert_board_kind`, `delete_board` |
| Tasks | `list_tasks`, `create_task`, `update_task`, `toggle_complete`, `move_task`, `convert_task_to_project`, `delete_task` |
| Sharing | `share_board`, `unshare_board`, `list_board_shares`, `share_task`, `unshare_task`, `share_tasks`, `list_task_shares` |
| Teams | `list_teams`, `add_team`, `rename_team`, `add_team_member`, `remove_team_member`, `delete_team` |
| Users | `list_users`, `add_user`, `set_user_flags`, `whoami`, `change_password` |
| Statuses | `list_statuses`, `add_status`, `update_status`, `delete_status` |
| Trash | `list_trash`, `restore_board`, `restore_task`, `purge_board`, `purge_task` |
| Insights | `dashboard_stats`, `list_events` |

## How it works

- Talks to the backend REST API at `http://localhost:8787` (stdlib `urllib`, no HTTP dep).
- Board names are resolved case-insensitively (exact, then partial), so chat can
  say "Personal Projects" or just "eyegenerate" and it lands on the right board.
- Users resolve by name, email, or id. Teams by name or id.
- Uses the `mcp` SDK v2 (`mcp.server.mcpserver.MCPServer`).

## Env vars

- `TASKS_API_URL` (default `http://localhost:8787`) — override if the backend
  moves ports or goes to a subdomain.
- `TASKS_API_TOKEN` — Bearer token for the production server (auth is mandatory
  there). Get one via `POST /api/auth/login` with the admin credentials.
  Example: `TASKS_API_URL=https://tasksmgr.rogeriogt.com TASKS_API_TOKEN=...`

## Setup (already done on this machine)

1. Dedicated venv: `mcp_server/.venv` (keeps `mcp` SDK's starlette from clashing
   with the backend's FastAPI pin).
2. Registered in Hermes: `hermes mcp add tasks_tracker --command .../.venv/bin/python --args .../server.py`
3. Tools appear as `mcp_tasks_tracker_*` in new sessions.

## Run manually

```bash
cd mcp_server
.venv/bin/python server.py
```

## Test

```bash
hermes mcp test tasks_tracker
```
