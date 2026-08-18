/* Typed fetch helpers — base URL /api (Vite proxy -> :8787) */

const BASE = "/api";
const TOKEN_KEY = "tasks_tracker_token";

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem(TOKEN_KEY);
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers || {}),
    },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/* Types matching backend schemas */
export type Board = {
  id: string;
  parent_id: string | null;
  name: string;
  kind: string;
  color: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type BoardTreeNode = {
  id: string;
  name: string;
  kind: string;
  color: string;
  sort_order: number;
  parent_id: string | null;
  children: BoardTreeNode[];
};

export type Task = {
  id: string;
  board_id: string;
  title: string;
  description: string | null;
  status: string; // custom statuses are user-defined; defaults: not_started|in_progress|waiting|done
  priority: "high" | "medium" | "low" | "none";
  assignee: string | null;
  due_date: string | null;
  tags: string[] | null;
  position: number;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type StatsSummary = {
  total: number;
  done: number;
  waiting: number;
  in_progress: number;
  not_started: number;
  completion_rate: number;
};

export type Event = {
  id: string;
  entity_type: string;
  entity_id: string;
  user_id: string | null;
  action: string;
  field: string | null;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
};

export type User = {
  id: string;
  email: string;
  name: string;
  locale: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
};

export type Share = {
  id: string;
  board_id: string;
  user_id: string | null;
  team_id: string | null;
  permission: "view" | "edit";
  created_at: string;
};

export type TaskShare = {
  id: string;
  task_id: string;
  user_id: string | null;
  team_id: string | null;
  permission: "view" | "edit";
  created_at: string;
};

export type TeamMember = {
  id: string;
  team_id: string;
  user_id: string;
  role: "member" | "admin";
  created_at: string;
};

export type Team = {
  id: string;
  name: string;
  created_by: string | null;
  created_at: string;
  members: TeamMember[];
};

export type Status = {
  id: string;
  name: string;
  color: string;
  sort_order: number;
  created_by: string | null;
  created_at: string;
};

/* Boards */
export function fetchBoards() {
  return req<Board[]>("/boards");
}
export function fetchBoardTree() {
  return req<BoardTreeNode[]>("/boards/tree");
}
export function createBoard(payload: { name: string; parent_id?: string | null; kind: string; color?: string; sort_order?: number }) {
  return req<Board>("/boards", { method: "POST", body: JSON.stringify(payload) });
}
export function updateBoard(id: string, payload: Partial<{ name: string; parent_id: string | null; kind: string; color: string; sort_order: number }>) {
  return req<Board>(`/boards/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}
export function deleteBoard(id: string) {
  return req<void>(`/boards/${id}`, { method: "DELETE" });
}

/* Tasks */
export type TaskListParams = {
  board_id?: string;
  include_descendants?: boolean;
  status?: string;
  priority?: string;
  assignee?: string;
  search?: string;
  sort?: string;
};

export function fetchTasks(params: TaskListParams = {}) {
  const q = new URLSearchParams();
  if (params.board_id) q.set("board_id", params.board_id);
  if (params.include_descendants) q.set("include_descendants", "true");
  if (params.status) q.set("status", params.status);
  if (params.priority) q.set("priority", params.priority);
  if (params.assignee) q.set("assignee", params.assignee);
  if (params.search) q.set("search", params.search);
  if (params.sort) q.set("sort", params.sort);
  const qs = q.toString();
  return req<Task[]>(`/tasks${qs ? `?${qs}` : ""}`);
}

export function createTask(payload: { board_id: string; title: string; description?: string | null; status?: string; priority?: string; assignee?: string | null; due_date?: string | null; tags?: string[] | null }) {
  return req<Task>("/tasks", { method: "POST", body: JSON.stringify(payload) });
}

export function updateTask(id: string, payload: Partial<{ title: string; description: string | null; status: string; priority: string; assignee: string | null; due_date: string | null; tags: string[] | null; position: number; board_id: string }>) {
  return req<Task>(`/tasks/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export function toggleComplete(id: string) {
  return req<Task>(`/tasks/${id}/complete`, { method: "POST" });
}

export function moveTask(id: string, payload: { board_id: string; position?: number }) {
  return req<Task>(`/tasks/${id}/move`, { method: "POST", body: JSON.stringify(payload) });
}

export function convertTaskToProject(id: string) {
  return req<{ board: Board; task: Task }>(`/tasks/${id}/convert`, { method: "POST" });
}

export function deleteTask(id: string) {
  return req<void>(`/tasks/${id}`, { method: "DELETE" });
}

export function fetchStats() {
  return req<StatsSummary>("/tasks/stats/summary");
}

/* Events */
export function fetchEvents(params: { entity_type?: string; action?: string; limit?: number } = {}) {
  const q = new URLSearchParams();
  if (params.entity_type) q.set("entity_type", params.entity_type);
  if (params.action) q.set("action", params.action);
  if (params.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return req<Event[]>(`/events${qs ? `?${qs}` : ""}`);
}

/* Auth */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function register(payload: { email: string; name?: string; password: string }) {
  return req<{ token: string; user: User }>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
export function login(payload: { email: string; password: string }) {
  return req<{ token: string; user: User }>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
export function fetchMe() {
  return req<User>("/auth/me");
}
export function fetchUsers() {
  return req<User[]>("/auth/users");
}

/* Sharing */
export function fetchAcl(boardId: string) {
  return req<Share[]>(`/boards/${boardId}/acl`);
}
export function shareBoard(boardId: string, payload: { user_id?: string | null; team_id?: string | null; permission: "view" | "edit" }) {
  return req<Share>(`/boards/${boardId}/acl`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
export function unshareBoard(boardId: string, aclId: string) {
  return req<void>(`/boards/${boardId}/acl/${aclId}`, { method: "DELETE" });
}

/* Task sharing */
export function fetchTaskAcl(taskId: string) {
  return req<TaskShare[]>(`/tasks/${taskId}/acl`);
}
export function shareTask(taskId: string, payload: { user_id?: string | null; team_id?: string | null; permission: "view" | "edit" }) {
  return req<TaskShare>(`/tasks/${taskId}/acl`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
export function unshareTask(taskId: string, aclId: string) {
  return req<void>(`/tasks/${taskId}/acl/${aclId}`, { method: "DELETE" });
}
export function shareTasksBatch(taskIds: string[], payload: { user_id?: string | null; team_id?: string | null; permission: "view" | "edit" }) {
  return req<{ created: number; updated: number }>(`/tasks/share`, {
    method: "POST",
    body: JSON.stringify({ task_ids: taskIds, ...payload }),
  });
}

/* Statuses */
export function fetchStatuses() {
  return req<Status[]>("/statuses");
}
export function createStatus(payload: { name: string; color?: string }) {
  return req<Status>("/statuses", { method: "POST", body: JSON.stringify(payload) });
}
export function updateStatus(id: string, payload: { name?: string; color?: string; sort_order?: number }) {
  return req<Status>(`/statuses/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
}
export function deleteStatus(id: string) {
  return req<void>(`/statuses/${id}`, { method: "DELETE" });
}

/* Teams */
export function fetchTeams() {
  return req<Team[]>("/teams");
}
export function createTeam(name: string) {
  return req<Team>("/teams", { method: "POST", body: JSON.stringify({ name }) });
}
export function renameTeam(id: string, name: string) {
  return req<Team>(`/teams/${id}`, { method: "PATCH", body: JSON.stringify({ name }) });
}
export function deleteTeam(id: string) {
  return req<void>(`/teams/${id}`, { method: "DELETE" });
}
export function addTeamMember(teamId: string, userId: string, role: "member" | "admin" = "member") {
  return req<TeamMember>(`/teams/${teamId}/members`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId, role }),
  });
}
export function removeTeamMember(teamId: string, userId: string) {
  return req<void>(`/teams/${teamId}/members/${userId}`, { method: "DELETE" });
}

/* Admin user management */
export function adminCreateUser(payload: { email: string; name?: string; password: string; is_admin?: boolean }) {
  return req<User>("/auth/users", { method: "POST", body: JSON.stringify(payload) });
}
export function adminUpdateUser(userId: string, payload: { name?: string; is_active?: boolean; is_admin?: boolean; password?: string }) {
  return req<User>(`/auth/users/${userId}`, { method: "PATCH", body: JSON.stringify(payload) });
}
export function changePassword(currentPassword: string, newPassword: string) {
  return req<void>("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
}
