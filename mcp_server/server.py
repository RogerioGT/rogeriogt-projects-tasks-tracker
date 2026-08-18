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
def list_boards(workspace: str | None = None) -> dict:
    """Return the board hierarchy with each board's id, name, kind, and color.
    workspace: main board name or id (optional; default shows all main boards' trees)."""
    if workspace:
        wid = _resolve_workspace(workspace)
        tree = _get(f"/api/boards/tree?workspace_id={wid}")
    else:
        tree = _get("/api/boards/tree")
    return {"tree": tree}


@mcp.tool(description="List tasks, optionally filtered by board, status, priority, assignee, or search text.")
def list_tasks(
    board: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    search: str | None = None,
    sort: str | None = None,
) -> dict:
    """board accepts a board name or id. status: not_started|in_progress|waiting|done (or custom).
    priority: high|medium|low|none. sort: position|created_at|due_date|title|priority|status."""
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
    if sort:
        params["sort"] = sort
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
    tags: list[str] | None = None,
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
        "tags": tags,
    }
    return _post("/api/tasks", payload)


@mcp.tool(description="Toggle a task between done and not-done by id.")
def toggle_complete(task_id: str) -> dict:
    """Mark a done task as not-started, or any other task as done."""
    return _post(f"/api/tasks/{task_id}/complete")


@mcp.tool(description="Update any field of a task (title, status, priority, assignee, due date, description, tags).")
def update_task(
    task_id: str,
    title: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    due_date: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
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
    if tags is not None:
        payload["tags"] = tags
    if not payload:
        raise RuntimeError("No fields provided to update.")
    return _patch(f"/api/tasks/{task_id}", payload)


@mcp.tool(description="Move a task to a different board.")
def move_task(task_id: str, board: str) -> dict:
    """board is the destination board name or id."""
    b = _resolve_board(board)
    return _post(f"/api/tasks/{task_id}/move", {"board_id": b["id"]})


@mcp.tool(description="Turn a task into a project board (task becomes its first task; add sub-tasks to it).")
def convert_task_to_project(task_id: str) -> dict:
    """The new board is nested under the task's current board and named after the task."""
    return _post(f"/api/tasks/{task_id}/convert")


@mcp.tool(description="Delete a task by id (soft delete: goes to Trash, restorable 30 days).")
def delete_task(task_id: str) -> dict:
    """Moves the task to the Trash. Use restore_task to bring it back."""
    _delete(f"/api/tasks/{task_id}")
    return {"deleted": task_id, "note": "soft-deleted; restorable for 30 days via restore_task"}


@mcp.tool(description="Add a new section, company, or project board.")
def add_board(
    name: str,
    kind: str = "project",
    parent: str | None = None,
    color: str | None = None,
    workspace: str | None = None,
) -> dict:
    """kind: section|company|project. parent is a parent board name or id (optional).
    workspace: main board name or id for new top-level sections (optional; defaults to the main board)."""
    payload = {"name": name, "kind": kind, "color": color}
    if parent:
        p = _resolve_board(parent)
        payload["parent_id"] = p["id"]
    elif workspace:
        payload["workspace_id"] = _resolve_workspace(workspace)
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


@mcp.tool(description="Delete a board and everything under it (soft delete: Trash, restorable 30 days).")
def delete_board(board: str) -> dict:
    """board is a board name or id. Moves the subtree to the Trash."""
    b = _resolve_board(board)
    _delete(f"/api/boards/{b['id']}")
    return {"deleted": b["id"], "name": b["name"], "note": "soft-deleted; restorable for 30 days via restore_board"}


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


@mcp.tool(description="Rename or recolor a custom workflow status (admin only).")
def update_status(status_id: str, name: str | None = None, color: str | None = None) -> dict:
    payload = {}
    if name is not None:
        payload["name"] = name
    if color is not None:
        payload["color"] = color
    if not payload:
        raise RuntimeError("Provide name and/or color.")
    return _patch(f"/api/statuses/{status_id}", payload)


# ---------------------------------------------------------------------------
# v1.3+ — board move/convert, teams mgmt, trash, events, ACL listing
# ---------------------------------------------------------------------------

@mcp.tool(description="Move or reorder a board in the hierarchy (drag-and-drop equivalent).")
def move_board(board: str, parent: str | None = None, position: int | None = None, to_top_level: bool = False) -> dict:
    """board and parent accept names or ids.
    - parent given: move under that parent.
    - to_top_level=True: move to the top level (sections).
    - neither: REORDER in place (keep the board's current parent), used with position.
    position = index among siblings (0 = first). Reindexes siblings."""
    b = _resolve_board(board)
    if parent:
        p = _resolve_board(parent)
        payload = {"parent_id": p["id"], "position": position}
    elif to_top_level:
        payload = {"parent_id": None, "position": position}
    else:
        # reorder among current siblings
        payload = {"parent_id": b.get("parent_id"), "position": position}
    return _post(f"/api/boards/{b['id']}/move", payload)


@mcp.tool(description="Convert a board's hierarchy level: project <-> company <-> section.")
def convert_board_kind(board: str, kind: str) -> dict:
    """kind: section|company|project. Converting to section moves it to top level."""
    b = _resolve_board(board)
    if kind not in ("section", "company", "project"):
        raise RuntimeError("kind must be section, company, or project")
    return _post(f"/api/boards/{b['id']}/convert", {"kind": kind})


@mcp.tool(description="List who a board is shared with (admin/users).")
def list_board_shares(board: str) -> dict:
    """board accepts a name or id. Returns ACL rows with user_id/team_id and permission."""
    b = _resolve_board(board)
    shares = _get(f"/api/boards/{b['id']}/acl")
    return {"board": b["name"], "shares": shares}


@mcp.tool(description="List who a task is shared with.")
def list_task_shares(task_id: str) -> dict:
    """Returns task ACL rows with user_id/team_id and permission."""
    shares = _get(f"/api/tasks/{task_id}/acl")
    return {"shares": shares}


@mcp.tool(description="Remove a task share (by ACL id; get ids from list_task_shares).")
def unshare_task(task_id: str, acl_id: str) -> dict:
    _delete(f"/api/tasks/{task_id}/acl/{acl_id}")
    return {"removed": acl_id}


@mcp.tool(description="Rename a team (admin only).")
def rename_team(team: str, name: str) -> dict:
    team_obj = _resolve_team(team)
    return _patch(f"/api/teams/{team_obj['id']}", {"name": name})


@mcp.tool(description="Delete a team and its shares (admin only).")
def delete_team(team: str) -> dict:
    team_obj = _resolve_team(team)
    _delete(f"/api/teams/{team_obj['id']}")
    return {"deleted": team_obj["id"], "name": team_obj["name"]}


@mcp.tool(description="Remove a user from a team (admin only).")
def remove_team_member(team: str, user: str) -> dict:
    team_obj = _resolve_team(team)
    user_obj = _resolve_user(user)
    _delete(f"/api/teams/{team_obj['id']}/members/{user_obj['id']}")
    return {"removed": user_obj["id"]}


@mcp.tool(description="List the Trash: soft-deleted boards and tasks with days until purge.")
def list_trash() -> dict:
    data = _get("/api/trash")
    return data if isinstance(data, dict) else {"trash": data}


@mcp.tool(description="Restore a soft-deleted board + its whole subtree from the Trash.")
def restore_board(board_id: str) -> dict:
    return _post(f"/api/trash/boards/{board_id}/restore")


@mcp.tool(description="Restore a soft-deleted task from the Trash.")
def restore_task(task_id: str) -> dict:
    return _post(f"/api/trash/tasks/{task_id}/restore")


@mcp.tool(description="Permanently delete a trashed board (no restore after this).")
def purge_board(board_id: str) -> dict:
    _delete(f"/api/trash/boards/{board_id}")
    return {"purged": board_id}


@mcp.tool(description="Permanently delete a trashed task (no restore after this).")
def purge_task(task_id: str) -> dict:
    _delete(f"/api/trash/tasks/{task_id}")
    return {"purged": task_id}


@mcp.tool(description="List the change history (who did what, when).")
def list_events(entity_type: str | None = None, action: str | None = None, limit: int = 100) -> dict:
    """entity_type: task|board. action: create|update|complete|reopen|move|delete|convert|share|restore."""
    params = {"limit": str(limit)}
    if entity_type:
        params["entity_type"] = entity_type
    if action:
        params["action"] = action
    qs = "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in params.items())
    events = _get(f"/api/events?{qs}")
    return {"events": events, "count": len(events) if isinstance(events, list) else 0}


@mcp.tool(description="Who is the current user (the token's identity).")
def whoami() -> dict:
    data = _get("/api/auth/me")
    return data if isinstance(data, dict) else {"user": data}


# ── Workspaces (main boards) ─────────────────────────────────────────────
@mcp.tool(description="List all main boards (workspaces) with board counts.")
def list_workspaces() -> dict:
    data = _get("/api/workspaces")
    return {"workspaces": data} if isinstance(data, list) else data


@mcp.tool(description="Create a new main board (workspace): a totally independent board with its own sections, columns and tasks.")
def add_workspace(name: str) -> dict:
    data = _post("/api/workspaces", {"name": name})
    return data if isinstance(data, dict) else {"workspace": data}


@mcp.tool(description="Rename a main board (workspace).")
def rename_workspace(workspace: str, name: str) -> dict:
    wid = _resolve_workspace(workspace)
    data = _patch(f"/api/workspaces/{wid}", {"name": name})
    return data if isinstance(data, dict) else {"workspace": data}


@mcp.tool(description="Delete a main board and everything in it (soft delete: goes to Trash, restorable 30 days).")
def delete_workspace(workspace: str) -> dict:
    wid = _resolve_workspace(workspace)
    _delete(f"/api/workspaces/{wid}")
    return {"deleted": wid}


@mcp.tool(description="Restore a soft-deleted main board from the Trash (everything inside comes back).")
def restore_workspace(workspace_id: str) -> dict:
    data = _post(f"/api/workspaces/{workspace_id}/restore", None)
    return data if isinstance(data, dict) else {"workspace": data}


@mcp.tool(description="Permanently delete a trashed main board and everything in it.")
def purge_workspace(workspace_id: str) -> dict:
    _delete(f"/api/workspaces/trash/{workspace_id}")
    return {"purged": workspace_id}


def _resolve_workspace(workspace: str) -> str:
    """Resolve a workspace by id or name (exact then partial match)."""
    data = _get("/api/workspaces")
    if not isinstance(data, list):
        raise RuntimeError(f"workspace lookup failed: {data}")
    ws_list = data
    for w in ws_list:
        if w.get("id") == workspace:
            return w["id"]
    for w in ws_list:
        if w.get("name") == workspace:
            return w["id"]
    for w in ws_list:
        n = w.get("name") or ""
        if workspace.lower() in n.lower():
            return w["id"]
    raise RuntimeError(f"workspace not found: {workspace!r} (available: {[w.get('name') for w in ws_list]})")


@mcp.tool(description="Change the current user's password.")
def change_password(current_password: str, new_password: str) -> dict:
    _post("/api/auth/change-password", {"current_password": current_password, "new_password": new_password})
    return {"changed": True}


if __name__ == "__main__":
    mcp.run(transport="stdio")
