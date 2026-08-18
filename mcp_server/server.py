"""MCP server for the Rogerio Projects & Tasks Tracker.

Exposes the backend REST API (http://localhost:8787) as MCP tools so Hermes
can drive the task board from chat: list sections, list/create/complete/move
tasks, add boards, and pull dashboard stats.

Uses stdlib urllib for HTTP (no third-party HTTP client needed) and the
`mcp` SDK v2 (`mcp.server.mcpserver.MCPServer`).

Run (from the mcp_server/ dir, with its .venv):
    .venv/bin/python server.py
"""

import json
import os
import urllib.request
import urllib.error
import urllib.parse

from mcp.server import mcpserver

API_BASE = os.environ.get("TASKS_API_URL", "http://localhost:8787")
API_TOKEN = os.environ.get("TASKS_API_TOKEN", "")


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib urllib)
# ---------------------------------------------------------------------------

def _request(method: str, path: str, payload: dict | None = None) -> dict | list:
    url = f"{API_BASE}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if API_TOKEN:
        headers["Authorization"] = f"Bearer {API_TOKEN}"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            if not body.strip():
                return {}
            return json.loads(body)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(detail).get("detail", detail)
        except Exception:
            pass
        raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Could not reach the tasks API at {API_BASE} (is it running? {e.reason})"
        ) from e


def _get(path: str) -> dict | list:
    return _request("GET", path)


def _post(path: str, payload: dict | None = None) -> dict:
    return _request("POST", path, payload)


def _patch(path: str, payload: dict) -> dict:
    return _request("PATCH", path, payload)


def _delete(path: str) -> None:
    _request("DELETE", path)


# ---------------------------------------------------------------------------
# Board resolution (accept name or id so chat feels natural)
# ---------------------------------------------------------------------------

def _resolve_board(name_or_id: str) -> dict:
    """Find a board by id, exact name (case-insensitive), or partial name.

    Raises RuntimeError with a helpful message if not found or ambiguous.
    """
    boards = _get("/api/boards")
    if not isinstance(boards, list):
        raise RuntimeError("Unexpected boards response from API")

    # 1. exact id
    for b in boards:
        if b.get("id") == name_or_id:
            return b

    # 2. exact name (case-insensitive)
    matches = [b for b in boards if b.get("name", "").lower() == name_or_id.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = ", ".join(b["name"] for b in matches)
        raise RuntimeError(f"Multiple boards named '{name_or_id}' ({names}). Use the id instead.")

    # 3. partial name match
    partial = [b for b in boards if name_or_id.lower() in b.get("name", "").lower()]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        names = ", ".join(f"{b['name']} ({b['id'][:8]})" for b in partial)
        raise RuntimeError(f"'{name_or_id}' matches multiple boards: {names}")

    raise RuntimeError(f"No board found matching '{name_or_id}'.")


# ---------------------------------------------------------------------------
# MCP server + tools
# ---------------------------------------------------------------------------

mcp = mcpserver.MCPServer(
    name="tasks-tracker",
    version="0.1.0",
    description="Drive Rogerio's Projects & Tasks Tracker (boards, tasks, stats).",
)


@mcp.tool(description="List all boards as a nested tree (sections -> companies -> projects).")
def list_boards() -> dict:
    """Return the full board hierarchy with each board's id, name, kind, and color."""
    tree = _get("/api/boards/tree")
    return {"tree": tree}


@mcp.tool(description="List tasks, optionally filtered by board, status, priority, assignee, or search text.")
def list_tasks(
    board: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    search: str | None = None,
) -> dict:
    """board accepts a board name or id. status: not_started|in_progress|waiting|done.
    priority: high|medium|low|none."""
    params = {}
    if board:
        b = _resolve_board(board)
        params["board_id"] = b["id"]
        params["include_descendants"] = "true"
    if status:
        params["status"] = status
    if priority:
        params["priority"] = priority
    if assignee:
        params["assignee"] = assignee
    if search:
        params["search"] = search
    qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    path = f"/api/tasks?{qs}" if qs else "/api/tasks"
    tasks = _get(path)
    return {"tasks": tasks, "count": len(tasks) if isinstance(tasks, list) else 0}


@mcp.tool(description="Create a new task on a board (new tasks appear at the top).")
def create_task(
    board: str,
    title: str,
    priority: str = "none",
    status: str = "not_started",
    assignee: str | None = None,
    due_date: str | None = None,
    description: str | None = None,
) -> dict:
    """board is a board name or id. due_date in YYYY-MM-DD format."""
    b = _resolve_board(board)
    payload = {
        "board_id": b["id"],
        "title": title,
        "priority": priority,
        "status": status,
        "assignee": assignee,
        "due_date": due_date,
        "description": description,
    }
    return _post("/api/tasks", payload)


@mcp.tool(description="Toggle a task between done and not-done by id.")
def toggle_complete(task_id: str) -> dict:
    """Mark a done task as not-started, or any other task as done."""
    return _post(f"/api/tasks/{task_id}/complete")


@mcp.tool(description="Update any field of a task (title, status, priority, assignee, due date, description).")
def update_task(
    task_id: str,
    title: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    due_date: str | None = None,
    description: str | None = None,
) -> dict:
    """Only the fields you provide are changed. due_date in YYYY-MM-DD format."""
    payload = {}
    if title is not None:
        payload["title"] = title
    if status is not None:
        payload["status"] = status
    if priority is not None:
        payload["priority"] = priority
    if assignee is not None:
        payload["assignee"] = assignee
    if due_date is not None:
        payload["due_date"] = due_date
    if description is not None:
        payload["description"] = description
    if not payload:
        raise RuntimeError("No fields provided to update.")
    return _patch(f"/api/tasks/{task_id}", payload)


@mcp.tool(description="Move a task to a different board.")
def move_task(task_id: str, board: str) -> dict:
    """board is the destination board name or id."""
    b = _resolve_board(board)
    return _post(f"/api/tasks/{task_id}/move", {"board_id": b["id"]})


@mcp.tool(description="Delete a task by id.")
def delete_task(task_id: str) -> dict:
    """Permanently remove a task."""
    _delete(f"/api/tasks/{task_id}")
    return {"deleted": task_id}


@mcp.tool(description="Add a new section, company, or project board.")
def add_board(
    name: str,
    kind: str = "project",
    parent: str | None = None,
    color: str | None = None,
) -> dict:
    """kind: section|company|project. parent is a parent board name or id (optional)."""
    payload = {"name": name, "kind": kind, "color": color}
    if parent:
        p = _resolve_board(parent)
        payload["parent_id"] = p["id"]
    return _post("/api/boards", payload)


@mcp.tool(description="Get dashboard stats: total, done, waiting, in-progress, not-started, completion rate.")
def dashboard_stats() -> dict:
    """Return task counts by status and overall completion rate."""
    return _get("/api/tasks/stats/summary")


# ---------------------------------------------------------------------------
# Phase 13 — admin & sharing tools
# ---------------------------------------------------------------------------

def _resolve_user(name_or_email_or_id: str) -> dict:
    users = _get("/api/auth/users")
    if not isinstance(users, list):
        raise RuntimeError("Unexpected users response from API")
    for u in users:
        if u.get("id") == name_or_email_or_id:
            return u
    matches = [u for u in users if u.get("email", "").lower() == name_or_email_or_id.lower()
               or u.get("name", "").lower() == name_or_email_or_id.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise RuntimeError(f"Multiple users match '{name_or_email_or_id}'.")
    raise RuntimeError(f"No user found matching '{name_or_email_or_id}'.")


def _resolve_team(name_or_id: str) -> dict:
    teams = _get("/api/teams")
    if not isinstance(teams, list):
        raise RuntimeError("Unexpected teams response from API")
    for team in teams:
        if team.get("id") == name_or_id:
            return team
    matches = [team for team in teams if team.get("name", "").lower() == name_or_id.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise RuntimeError(f"Multiple teams match '{name_or_id}'.")
    raise RuntimeError(f"No team found matching '{name_or_id}'.")


@mcp.tool(description="Rename or recolor a board (company/project/section).")
def update_board(board: str, name: str | None = None, color: str | None = None) -> dict:
    """board is a board name or id. Only provided fields change."""
    b = _resolve_board(board)
    payload = {}
    if name is not None:
        payload["name"] = name
    if color is not None:
        payload["color"] = color
    if not payload:
        raise RuntimeError("Provide name and/or color.")
    return _patch(f"/api/boards/{b['id']}", payload)


@mcp.tool(description="Delete a board and everything under it (projects, tasks).")
def delete_board(board: str) -> dict:
    """board is a board name or id. Destructive; removes descendants."""
    b = _resolve_board(board)
    _delete(f"/api/boards/{b['id']}")
    return {"deleted": b["id"], "name": b["name"]}


@mcp.tool(description="List all users (admin only in production mode).")
def list_users() -> dict:
    """Return users with email, name, active, admin flags."""
    users = _get("/api/auth/users")
    return {"users": users}


@mcp.tool(description="Create a new user account (admin only).")
def add_user(email: str, password: str, name: str = "", is_admin: bool = False) -> dict:
    """The new user logs in with email + password."""
    return _post("/api/auth/users", {"email": email, "password": password, "name": name, "is_admin": is_admin})


@mcp.tool(description="Activate, deactivate, or toggle admin for a user (admin only).")
def set_user_flags(user: str, is_active: bool | None = None, is_admin: bool | None = None) -> dict:
    """user is a name, email, or id. Only provided flags change."""
    u = _resolve_user(user)
    payload = {}
    if is_active is not None:
        payload["is_active"] = is_active
    if is_admin is not None:
        payload["is_admin"] = is_admin
    if not payload:
        raise RuntimeError("Provide is_active and/or is_admin.")
    return _patch(f"/api/auth/users/{u['id']}", payload)


@mcp.tool(description="List all teams with their members (admin only).")
def list_teams() -> dict:
    teams = _get("/api/teams")
    return {"teams": teams}


@mcp.tool(description="Create a new team (admin only).")
def add_team(name: str) -> dict:
    return _post("/api/teams", {"name": name})


@mcp.tool(description="Add a user to a team (admin only).")
def add_team_member(team: str, user: str, role: str = "member") -> dict:
    """role: member | admin. team and user accept names, emails, or ids."""
    team_obj = _resolve_team(team)
    user_obj = _resolve_user(user)
    return _post(f"/api/teams/{team_obj['id']}/members", {"user_id": user_obj["id"], "role": role})


@mcp.tool(description="Share a board subtree (project, company, or section) with a user or team.")
def share_board(board: str, user: str | None = None, team: str | None = None, permission: str = "edit") -> dict:
    """Provide user OR team (name/email/id). Sharing inherits down the tree."""
    b = _resolve_board(board)
    payload = {"permission": permission}
    if user:
        payload["user_id"] = _resolve_user(user)["id"]
    elif team:
        payload["team_id"] = _resolve_team(team)["id"]
    else:
        raise RuntimeError("Provide user or team.")
    return _post(f"/api/boards/{b['id']}/acl", payload)


@mcp.tool(description="Remove a board share (by ACL id; see share_board result or list acl).")
def unshare_board(board: str, acl_id: str) -> dict:
    b = _resolve_board(board)
    _delete(f"/api/boards/{b['id']}/acl/{acl_id}")
    return {"removed": acl_id}


@mcp.tool(description="Share a single task with a user or team.")
def share_task(task_id: str, user: str | None = None, team: str | None = None, permission: str = "edit") -> dict:
    """Provide user OR team (name/email/id)."""
    payload = {"permission": permission}
    if user:
        payload["user_id"] = _resolve_user(user)["id"]
    elif team:
        payload["team_id"] = _resolve_team(team)["id"]
    else:
        raise RuntimeError("Provide user or team.")
    return _post(f"/api/tasks/{task_id}/acl", payload)


@mcp.tool(description="Share a selected list of task ids with a user or team in one call.")
def share_tasks(task_ids: list[str], user: str | None = None, team: str | None = None, permission: str = "edit") -> dict:
    """task_ids is a list of task ids. Provide user OR team."""
    payload = {"task_ids": task_ids, "permission": permission}
    if user:
        payload["user_id"] = _resolve_user(user)["id"]
    elif team:
        payload["team_id"] = _resolve_team(team)["id"]
    else:
        raise RuntimeError("Provide user or team.")
    return _post("/api/tasks/share", payload)


@mcp.tool(description="List custom workflow statuses (Kanban columns).")
def list_statuses() -> dict:
    """Return status names with their colors, in display order."""
    statuses = _get("/api/statuses")
    return {"statuses": statuses}


@mcp.tool(description="Add a custom workflow status (becomes a Kanban column).")
def add_status(name: str, color: str | None = None) -> dict:
    """Any logged-in user can add a status; admins can delete them."""
    return _post("/api/statuses", {"name": name, "color": color})


@mcp.tool(description="Delete a custom workflow status by id (admin only). Tasks keep their status text.")
def delete_status(status_id: str) -> dict:
    _delete(f"/api/statuses/{status_id}")
    return {"deleted": status_id}


if __name__ == "__main__":
    mcp.run(transport="stdio")
