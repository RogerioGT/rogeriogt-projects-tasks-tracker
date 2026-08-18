# MCP Server — Tasks Tracker

Lets Hermes drive the task board from chat. Type "add task X to eyegenerate.com"
and the MCP tools resolve the board name and create the task.

## What it exposes

| Tool | What it does |
|------|--------------|
| `list_boards` | Full hierarchy: sections -> companies -> projects |
| `list_tasks` | Filter by board/status/priority/assignee/search |
| `create_task` | New task (board can be a name or id) |
| `toggle_complete` | Done <-> not-started |
| `update_task` | Change any field |
| `move_task` | Move to another board |
| `delete_task` | Delete |
| `add_board` | New section / company / project |
| `dashboard_stats` | Counts + completion rate |

## How it works

- Talks to the backend REST API at `http://localhost:8787` (stdlib `urllib`, no HTTP dep).
- Board names are resolved case-insensitively (exact, then partial), so chat can
  say "Personal Projects" or just "eyegenerate" and it lands on the right board.
- Uses the `mcp` SDK v2 (`mcp.server.mcpserver.MCPServer`).

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

## Env vars

- `TASKS_API_URL` (default `http://localhost:8787`) — override if the backend
  moves ports or goes to a subdomain.
