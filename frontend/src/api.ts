/* Typed fetch helpers — base URL /api (Vite proxy -> :8787) */

const BASE = "/api";

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
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
  status: "not_started" | "in_progress" | "waiting" | "done";
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

export function deleteTask(id: string) {
  return req<void>(`/tasks/${id}`, { method: "DELETE" });
}

export function fetchStats() {
  return req<StatsSummary>("/tasks/stats/summary");
}
