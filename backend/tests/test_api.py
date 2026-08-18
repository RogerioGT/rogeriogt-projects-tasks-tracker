"""End-to-end API tests: admin, regular user, and anonymous scenarios.

Run:
  REQUIRE_AUTH=true ADMIN_EMAIL=admin@rogeriogt.com ADMIN_PASSWORD=test1234 \
  DATA_DIR=/tmp/tt-test-data .venv/bin/python tests/test_api.py
"""
import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: E402


def main():
    with TestClient(app) as c:
        # ── Anonymous ──────────────────────────────────────────────
        assert c.get("/api/boards").status_code == 401, "anon boards should 401"
        assert c.get("/api/auth/required").json()["required"] is True

        # ── Admin login ────────────────────────────────────────────
        r = c.post("/api/auth/login", json={"email": "admin@rogeriogt.com", "password": "test1234"})
        assert r.status_code == 200, r.text
        admin = {"Authorization": f"Bearer {r.json()['token']}"}
        admin_id = r.json()["user"]["id"]
        assert r.json()["user"]["is_admin"] is True

        # ── Admin creates users ────────────────────────────────────
        r = c.post("/api/auth/users", json={"email": "bob@x.com", "name": "Bob", "password": "bobpass123"}, headers=admin)
        assert r.status_code == 201, r.text
        bob_id = r.json()["id"]
        assert r.json()["is_admin"] is False

        r = c.post("/api/auth/users", json={"email": "carol@x.com", "name": "Carol", "password": "carolpass123"}, headers=admin)
        assert r.status_code == 201
        carol_id = r.json()["id"]

        # ── Teams ──────────────────────────────────────────────────
        r = c.post("/api/teams", json={"name": "Design Team"}, headers=admin)
        assert r.status_code == 201, r.text
        team_id = r.json()["id"]
        r = c.post(f"/api/teams/{team_id}/members", json={"user_id": bob_id, "role": "member"}, headers=admin)
        assert r.status_code == 201
        r = c.post(f"/api/teams/{team_id}/members", json={"user_id": carol_id}, headers=admin)
        assert r.status_code == 201
        teams = c.get("/api/teams", headers=admin).json()
        assert len(teams) == 1 and len(teams[0]["members"]) == 2

        # non-admin cannot create teams
        bob = {"Authorization": f"Bearer {c.post('/api/auth/login', json={'email': 'bob@x.com', 'password': 'bobpass123'}).json()['token']}"}
        assert c.post("/api/teams", json={"name": "Nope"}, headers=bob).status_code == 403

        # ── Regular users see NOTHING initially (no shares, no own boards) ──
        assert c.get("/api/boards", headers=bob).json() == []
        assert c.get("/api/tasks", headers=bob).json() == []

        # ── Admin creates a company + project ──────────────────────
        r = c.post("/api/boards", json={"name": "Test Company", "kind": "company"}, headers=admin)
        company_id = r.json()["id"]
        r = c.post("/api/boards", json={"name": "Test Project", "kind": "project", "parent_id": company_id}, headers=admin)
        project_id = r.json()["id"]
        r = c.post("/api/tasks", json={"board_id": project_id, "title": "Secret task"}, headers=admin)
        task_id = r.json()["id"]

        # bob still sees nothing
        assert c.get("/api/boards", headers=bob).json() == []
        # bob cannot edit admin's project
        assert c.patch(f"/api/boards/{project_id}", json={"name": "hacked"}, headers=bob).status_code == 403

        # ── Share the PROJECT with bob (edit) ──────────────────────
        r = c.post(f"/api/boards/{project_id}/acl", json={"user_id": bob_id, "permission": "edit"}, headers=admin)
        assert r.status_code == 201
        bob_boards = c.get("/api/boards", headers=bob).json()
        names = [b["name"] for b in bob_boards]
        assert "Test Project" in names, names
        assert "Test Company" not in names, "sharing a project must NOT expose the parent company"
        # bob can now edit the project
        assert c.patch(f"/api/boards/{project_id}", json={"name": "Test Project v2"}, headers=bob).status_code == 200
        # and sees the task
        bob_tasks = c.get("/api/tasks", headers=bob).json()
        assert any(t["id"] == task_id for t in bob_tasks)
        # and can edit the task
        assert c.patch(f"/api/tasks/{task_id}", json={"title": "Secret task v2"}, headers=bob).status_code == 200

        # ── Share the COMPANY with carol (view) ────────────────────
        r = c.post(f"/api/boards/{company_id}/acl", json={"user_id": carol_id, "permission": "view"}, headers=admin)
        assert r.status_code == 201
        carol = {"Authorization": f"Bearer {c.post('/api/auth/login', json={'email': 'carol@x.com', 'password': 'carolpass123'}).json()['token']}"}
        carol_boards = c.get("/api/boards", headers=carol).json()
        names = [b["name"] for b in carol_boards]
        assert "Test Company" in names and "Test Project v2" in names, names
        # view only: cannot edit
        assert c.patch(f"/api/boards/{project_id}", json={"name": "x"}, headers=carol).status_code == 403
        assert c.patch(f"/api/tasks/{task_id}", json={"title": "x"}, headers=carol).status_code == 403

        # ── Team sharing: share company with Design Team (view) ────
        r = c.post(f"/api/boards/{company_id}/acl", json={"team_id": team_id, "permission": "view"}, headers=admin)
        assert r.status_code == 201
        # bob (team member) also gains view on company + descendants; he keeps edit on project
        bob_boards = c.get("/api/boards", headers=bob).json()
        assert "Test Company" in [b["name"] for b in bob_boards]

        # ── Task-level share (bob shares a task with carol) ────────
        r = c.post(f"/api/tasks/{task_id}/acl", json={"user_id": carol_id, "permission": "edit"}, headers=bob)
        assert r.status_code == 201
        assert c.patch(f"/api/tasks/{task_id}", json={"title": "Carol can edit now"}, headers=carol).status_code == 200

        # ── Batch task share ───────────────────────────────────────
        t2 = c.post("/api/tasks", json={"board_id": project_id, "title": "Batch me"}, headers=admin).json()["id"]
        t3 = c.post("/api/tasks", json={"board_id": project_id, "title": "Batch me too"}, headers=admin).json()["id"]
        r = c.post("/api/tasks/share", json={"task_ids": [t2, t3], "user_id": carol_id, "permission": "view"}, headers=admin)
        assert r.status_code == 201 and r.json()["created"] == 2, r.text
        # carol can see them
        carol_tasks = {t["id"] for t in c.get("/api/tasks", headers=carol).json()}
        assert t2 in carol_tasks and t3 in carol_tasks

        # ── Change password ────────────────────────────────────────
        assert c.post("/api/auth/change-password", json={"current_password": "bobpass123", "new_password": "newpass456"}, headers=bob).status_code == 204
        assert c.post("/api/auth/login", json={"email": "bob@x.com", "password": "bobpass123"}).status_code == 401
        assert c.post("/api/auth/login", json={"email": "bob@x.com", "password": "newpass456"}).status_code == 200

        # ── Deactivate bob ─────────────────────────────────────────
        assert c.patch(f"/api/auth/users/{bob_id}", json={"is_active": False}, headers=admin).status_code == 200
        assert c.post("/api/auth/login", json={"email": "bob@x.com", "password": "newpass456"}).status_code == 403
        # his old token is now rejected (401 login required)
        assert c.get("/api/boards", headers=bob).status_code == 401

        # ── Dashboard stats respect visibility ─────────────────────
        bob_stats = c.get("/api/tasks/stats/summary", headers=carol).json()
        assert bob_stats["total"] >= 3

        # ── Custom statuses ────────────────────────────────────────
        statuses = c.get("/api/statuses", headers=admin).json()
        names = [s["name"] for s in statuses]
        assert names == ["not_started", "in_progress", "waiting", "done"], names
        # any user can add a status
        r = c.post("/api/statuses", json={"name": "In Review", "color": "#8b5cf6"}, headers=carol)
        assert r.status_code == 201, r.text
        # duplicate name -> 409
        assert c.post("/api/statuses", json={"name": "In Review"}, headers=carol).status_code == 409
        # tasks can use the custom status
        assert c.patch(f"/api/tasks/{t2}", json={"status": "In Review"}, headers=admin).status_code == 200
        # non-admin cannot delete a status
        assert c.delete(f"/api/statuses/{r.json()['id']}", headers=carol).status_code == 403
        # admin can delete; existing tasks keep the string
        assert c.delete(f"/api/statuses/{r.json()['id']}", headers=admin).status_code == 204
        still = c.get("/api/tasks", headers=carol).json()
        assert any(t["id"] == t2 and t["status"] == "In Review" for t in still)

        # ── Team delete with members + shares (was 500) ────────────
        r = c.post("/api/teams", json={"name": "To Delete"}, headers=admin)
        team2 = r.json()["id"]
        c.post(f"/api/teams/{team2}/members", json={"user_id": bob_id}, headers=admin)
        c.post(f"/api/boards/{company_id}/acl", json={"team_id": team2, "permission": "view"}, headers=admin)
        assert c.delete(f"/api/teams/{team2}", headers=admin).status_code == 204
        assert c.get(f"/api/teams", headers=admin).status_code == 200
        # duplicate member -> 409 (friendly, not 500)
        c.post(f"/api/teams/{team_id}/members", json={"user_id": bob_id}, headers=admin)
        assert c.post(f"/api/teams/{team_id}/members", json={"user_id": bob_id}, headers=admin).status_code == 409

        # ── Task -> project conversion ─────────────────────────────
        r = c.post("/api/tasks", json={"board_id": project_id, "title": "Grows into a project"}, headers=admin)
        grow_id = r.json()["id"]
        r = c.post(f"/api/tasks/{grow_id}/convert", headers=admin)
        assert r.status_code == 201, r.text
        body = r.json()
        new_board_id = body["board"]["id"]
        assert body["board"]["name"] == "Grows into a project"
        assert body["board"]["kind"] == "project"
        assert body["board"]["parent_id"] == project_id
        assert body["task"]["board_id"] == new_board_id, "task must move into the new project"
        # sub-tasks can now be added under the new project board
        r = c.post("/api/tasks", json={"board_id": new_board_id, "title": "Sub task one"}, headers=admin)
        assert r.status_code == 201
        r = c.post("/api/tasks", json={"board_id": new_board_id, "title": "Sub task two"}, headers=admin)
        assert r.status_code == 201
        subtasks = [t for t in c.get("/api/tasks", headers=admin).json() if t["board_id"] == new_board_id]
        assert len(subtasks) == 3, "original task + 2 sub-tasks"
        # non-editors cannot convert
        assert c.post(f"/api/tasks/{grow_id}/convert", headers=carol).status_code == 403

        # ── Sorting verification ───────────────────────────────────
        # create tasks with known titles/priorities/due dates on the project
        dates = ["2026-03-01", "2026-01-01", "2026-02-01", None]
        for i, d in enumerate(dates):
            c.post("/api/tasks", json={
                "board_id": project_id,
                "title": f"Sort test {i}",
                "priority": ["medium", "high", "low", "none"][i],
                "due_date": d,
            }, headers=admin)
        st = c.get("/api/tasks?board_id=" + project_id, headers=admin).json()
        titles = [t["title"] for t in st]
        assert titles[0] == "Sort test 3", f"position sort should put newest first, got {titles}"
        # title sort ascending
        st = c.get(f"/api/tasks?board_id={project_id}&sort=title", headers=admin).json()
        tsorted = sorted([t["title"] for t in st])
        assert [t["title"] for t in st] == tsorted, "title sort must be alphabetical"
        # priority sort semantic (high first)
        st = c.get(f"/api/tasks?board_id={project_id}&sort=priority", headers=admin).json()
        prios = [t["priority"] for t in st]
        assert prios[0] == "high" and prios[-1] == "none", f"priority order wrong: {prios}"
        # due_date sort: earliest first, nulls last
        st = c.get(f"/api/tasks?board_id={project_id}&sort=due_date", headers=admin).json()
        dues = [t["due_date"] for t in st]
        non_null = [d for d in dues if d]
        assert non_null == sorted(non_null), f"due_date must be ascending, got {dues}"
        assert dues[-1] is None or all(dues[-1:] and d is None for d in dues[-1:]), "nulls should sort last"
        # status sort semantic
        st = c.get(f"/api/tasks?board_id={project_id}&sort=status", headers=admin).json()
        assert st[0]["status"] in ("in_progress", "waiting", "not_started", "done")

        # ── Board move / reorder (drag & drop) ─────────────────────
        # create two more projects under the company
        p2 = c.post("/api/boards", json={"name": "Proj B", "kind": "project", "parent_id": company_id}, headers=admin).json()["id"]
        p3 = c.post("/api/boards", json={"name": "Proj C", "kind": "project", "parent_id": company_id}, headers=admin).json()["id"]
        # reorder: move p3 to position 0 (leftmost)
        r = c.post(f"/api/boards/{p3}/move", json={"parent_id": company_id, "position": 0}, headers=admin)
        assert r.status_code == 200, r.text
        order = [b["name"] for b in c.get(f"/api/boards", headers=admin).json() if b["parent_id"] == company_id]
        assert order[0] == "Proj C", f"Proj C should be leftmost, got {order}"
        # move a project into another project (nested move)
        r = c.post(f"/api/boards/{p2}/move", json={"parent_id": project_id, "position": 0}, headers=admin)
        assert r.status_code == 200, r.text
        assert r.json()["parent_id"] == project_id
        # move to top level
        r = c.post(f"/api/boards/{p2}/move", json={"parent_id": None, "position": 0}, headers=admin)
        assert r.status_code == 200 and r.json()["parent_id"] is None
        # cycle guard: cannot move a parent under its own child
        r = c.post(f"/api/boards/{company_id}/move", json={"parent_id": p3, "position": 0}, headers=admin)
        assert r.status_code == 400, "cycle must be rejected"
        # self-parent guard
        r = c.post(f"/api/boards/{p3}/move", json={"parent_id": p3, "position": 0}, headers=admin)
        assert r.status_code == 400
        # permission: carol (view only) cannot move
        assert c.post(f"/api/boards/{p3}/move", json={"parent_id": company_id, "position": 1}, headers=carol).status_code == 403

        # ── Events carry user_name ─────────────────────────────────
        evs = c.get("/api/events?limit=50", headers=admin).json()
        assert any(e["action"] == "move" and e["user_name"] for e in evs), "move events must include user_name"
        names = {e["user_name"] for e in evs if e["user_name"]}
        assert "Admin" in names, f"expected admin name in events, got {names}"

        # ── Task share exposes the board chain (not siblings) ──────
        # dave gets ONLY a task share (no board share) on the project
        r = c.post("/api/auth/users", json={"email": "dave@x.com", "name": "Dave", "password": "davepass123"}, headers=admin)
        dave_id = r.json()["id"]
        dave = {"Authorization": f"Bearer {c.post('/api/auth/login', json={'email': 'dave@x.com', 'password': 'davepass123'}).json()['token']}"}
        c.post(f"/api/tasks/{t2}/acl", json={"user_id": dave_id, "permission": "view"}, headers=admin)
        dave_boards = c.get("/api/boards", headers=dave).json()
        dave_ids = {b["id"] for b in dave_boards}
        # chain: section -> company -> project must be visible
        assert company_id in dave_ids, "task share must reveal the company (ancestor)"
        assert project_id in dave_ids, "task share must reveal the project (task's board)"
        # sibling projects must NOT leak
        assert p2 not in dave_ids and p3 not in dave_ids, "siblings must stay hidden"
        # dave sees only the shared task inside that board
        dave_tasks = c.get("/api/tasks", headers=dave).json()
        assert [t["id"] for t in dave_tasks] == [t2], "only the shared task should be visible"
        # tree carries permission for dave: view on the chain, no edit
        tree = c.get("/api/boards/tree", headers=dave).json()
        flat = []
        def walk(nodes):
            for n in nodes:
                flat.append(n)
                walk(n["children"])
        walk(tree)
        perms = {n["id"]: n.get("permission") for n in flat}
        assert perms.get(project_id) in (None, "view"), "no edit permission from a task share"
        # board delete with task shares must succeed (FK cleanup)
        assert c.delete(f"/api/boards/{new_board_id}", headers=admin).status_code == 204

        # ── Soft delete + trash + restore ──────────────────────────
        # delete a project with tasks + a sub-board
        r = c.post("/api/boards", json={"name": "To Trash", "kind": "project", "parent_id": company_id}, headers=admin)
        trash_proj = r.json()["id"]
        c.post("/api/tasks", json={"board_id": trash_proj, "title": "Will be trashed"}, headers=admin)
        c.post("/api/boards", json={"name": "Sub of trash", "kind": "project", "parent_id": trash_proj}, headers=admin)
        assert c.delete(f"/api/boards/{trash_proj}", headers=admin).status_code == 204
        # gone from boards/tasks
        ids = {b["id"] for b in c.get("/api/boards", headers=admin).json()}
        assert trash_proj not in ids, "soft-deleted board must disappear from list"
        task_ids = {t["id"] for t in c.get("/api/tasks", headers=admin).json()}
        trashed_task = next(
            t["id"] for t in c.get("/api/tasks", headers=admin).json()
        ) if False else None
        # trash lists it (admin)
        trash_list = c.get("/api/trash", headers=admin).json()
        trash_names = [b["name"] for b in trash_list["boards"]]
        assert "To Trash" in trash_names, trash_names
        assert "Sub of trash" not in trash_names, "children should not be listed separately"
        # non-admin cannot see trash
        assert c.get("/api/trash", headers=carol).status_code == 403
        # restore
        assert c.post(f"/api/trash/boards/{trash_proj}/restore", headers=admin).status_code == 200
        ids = {b["id"] for b in c.get("/api/boards", headers=admin).json()}
        assert trash_proj in ids, "restore must bring the board back"
        sub = next(b["id"] for b in c.get("/api/boards", headers=admin).json() if b["name"] == "Sub of trash")
        tasks_after = c.get(f"/api/tasks?board_id={sub}", headers=admin).json()
        # task soft delete
        r = c.post("/api/tasks", json={"board_id": trash_proj, "title": "Task to trash"}, headers=admin)
        t_trash = r.json()["id"]
        assert c.delete(f"/api/tasks/{t_trash}", headers=admin).status_code == 204
        assert t_trash not in {t["id"] for t in c.get("/api/tasks", headers=admin).json()}
        trash_list = c.get("/api/trash", headers=admin).json()
        assert t_trash in [t["id"] for t in trash_list["tasks"]]
        assert c.post(f"/api/trash/tasks/{t_trash}/restore", headers=admin).status_code == 200
        assert t_trash in {t["id"] for t in c.get("/api/tasks", headers=admin).json()}

        # ── Hierarchy kind conversion ──────────────────────────────
        # convert a project to a company
        r = c.post(f"/api/boards/{p3}/convert", json={"kind": "company"}, headers=admin)
        assert r.status_code == 200 and r.json()["kind"] == "company"
        # convert project to section -> moves to top level
        r = c.post(f"/api/boards/{p2}/convert", json={"kind": "section"}, headers=admin)
        assert r.status_code == 200 and r.json()["kind"] == "section"
        assert r.json()["parent_id"] is None, "converting to section must move it to top level"
        # section -> project stays put (top level)
        r = c.post(f"/api/boards/{p2}/convert", json={"kind": "project"}, headers=admin)
        assert r.status_code == 200 and r.json()["kind"] == "project"
        # invalid kind
        assert c.post(f"/api/boards/{p2}/convert", json={"kind": "nonsense"}, headers=admin).status_code == 400
        # carol cannot convert
        assert c.post(f"/api/boards/{p2}/convert", json={"kind": "company"}, headers=carol).status_code == 403

        print("ALL API TESTS PASS")
        print(f"  users: admin + bob + carol; team: {team_id}")
        print(f"  boards: company + project; tasks: secret + 2 batch; custom status flow verified")


if __name__ == "__main__":
    main()
