import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchBoards, fetchTasks, createTask, toggleComplete, Task } from "../api";
import { useI18n } from "../i18n";
import FilterBar, { EMPTY_FILTERS, Filters, filtersToQuery } from "../components/FilterBar";
import TaskEditDialog from "../components/TaskEditDialog";

const priorityDot: Record<string, string> = { high: "#ef4444", medium: "#f97316", low: "#3b82f6", none: "#6b7280" };

export default function CompactView({ search }: { search: string }) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const { data: boards } = useQuery({ queryKey: ["boards", "flat"], queryFn: fetchBoards });
  const boardName = new Map((boards || []).map((b) => [b.id, b.name]));
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);

  const { data: tasks } = useQuery({
    queryKey: ["tasks", "compact", search, filters],
    queryFn: () => fetchTasks({ ...filtersToQuery(filters), search: search || undefined, sort: "created_at" }),
  });

  const [title, setTitle] = useState("");
  const [targetBoard, setTargetBoard] = useState<string>("");
  const [editingTask, setEditingTask] = useState<Task | null>(null);

  // default board = first available
  const effectiveBoard = targetBoard || (boards && boards[0]?.id) || "";

  const createMut = useMutation({
    mutationFn: () => createTask({ board_id: effectiveBoard, title: title.trim() }),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      setTitle("");
    },
  });

  const toggleMut = useMutation({
    mutationFn: (id: string) => toggleComplete(id),
    onSettled: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !effectiveBoard) return;
    createMut.mutate();
  };

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", padding: 8, display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        <FilterBar filters={filters} onChange={setFilters} />
      </div>
      <form onSubmit={handleAdd} style={{ display: "flex", gap: 6, position: "sticky", top: 0, background: "var(--bg)", padding: "6px 0", zIndex: 1 }}>
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t("newTaskPlaceholder")} style={{ flex: 1, fontSize: 11, padding: "6px 8px", border: "1px solid var(--border)", borderRadius: 4, background: "var(--bg-surface)", color: "var(--text)" }} />
        <select value={effectiveBoard} onChange={(e) => setTargetBoard(e.target.value)} style={{ fontSize: 11, padding: "6px 8px", border: "1px solid var(--border)", borderRadius: 4, background: "var(--bg-surface)", color: "var(--text)" }}>
          {(boards || []).map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
        <button type="submit" style={{ fontSize: 11, padding: "6px 12px", borderRadius: 4, border: "1px solid #3b82f6", background: "#3b82f6", color: "#fff", cursor: "pointer", whiteSpace: "nowrap" }}>
          {t("addTask")}
        </button>
      </form>

      <div style={{ display: "flex", flexDirection: "column", border: "1px solid var(--border)", borderRadius: 6, overflow: "hidden", background: "var(--bg-surface)" }}>
        {(tasks || []).map((task: Task) => (
          <div
            key={task.id}
            onClick={() => setEditingTask(task)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "5px 8px",
              borderBottom: "1px solid var(--border)",
              minHeight: "var(--row-h)",
              background: task.status === "done" ? "var(--bg)" : "var(--bg-surface)",
              opacity: task.status === "done" ? 0.6 : 1,
              cursor: "pointer",
            }}
          >
            <input type="checkbox" checked={task.status === "done"} onChange={() => toggleMut.mutate(task.id)} onClick={(e) => e.stopPropagation()} style={{ accentColor: "#22c55e", width: 12, height: 12, flexShrink: 0 }} />
            <span style={{ width: 7, height: 7, borderRadius: 99, background: priorityDot[task.priority], flexShrink: 0 }} />
            <span style={{ flex: 1, fontSize: 11, color: task.status === "done" ? "var(--text-faint)" : "var(--text)", textDecoration: task.status === "done" ? "line-through" : "none", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {task.title}
            </span>
            <span style={{ fontSize: 10, color: "var(--text-faint)", whiteSpace: "nowrap" }}>{boardName.get(task.board_id) || ""}</span>
            {task.due_date && <span style={{ fontSize: 10, color: "var(--text-faint)" }}>{task.due_date}</span>}
          </div>
        ))}
        {(tasks || []).length === 0 && <div style={{ padding: 16, textAlign: "center", fontSize: 11, color: "var(--text-faint)" }}>{t("noTasks")}</div>}
      </div>

      <div style={{ fontSize: 10, color: "var(--text-faint)", textAlign: "center" }}>{(tasks || []).length} tasks · most recent first · click a task to edit</div>

      {editingTask && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 60 }} onClick={() => setEditingTask(null)}>
          <TaskEditDialog task={editingTask} onClose={() => setEditingTask(null)} />
        </div>
      )}
    </div>
  );
}
