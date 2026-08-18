import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchTasks, updateTask, Task } from "../api";
import { useI18n } from "../i18n";
import FilterBar, { EMPTY_FILTERS, Filters, filtersToQuery } from "../components/FilterBar";

const statuses: Task["status"][] = ["not_started", "in_progress", "waiting", "done"];
const statusColor: Record<string, string> = {
  not_started: "#6b7280",
  in_progress: "#3b82f6",
  waiting: "#eab308",
  done: "#22c55e",
};

export default function KanbanView({ search }: { search: string }) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const { data: tasks } = useQuery({
    queryKey: ["tasks", "kanban", filters, search],
    queryFn: () => fetchTasks({ ...filtersToQuery(filters), search: search || undefined }),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, status }: { id: string; status: Task["status"] }) => updateTask(id, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const handleDragStart = (e: React.DragEvent, task: Task) => {
    e.dataTransfer.setData("text/plain", task.id);
    e.dataTransfer.effectAllowed = "move";
  };
  const handleDrop = (e: React.DragEvent, status: Task["status"]) => {
    e.preventDefault();
    const id = e.dataTransfer.getData("text/plain");
    if (id) updateMut.mutate({ id, status });
  };

  return (
    <div style={{ padding: 8, display: "flex", flexDirection: "column", gap: 8, height: "100%" }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
        <FilterBar filters={filters} onChange={setFilters} />
        <span style={{ fontSize: 10, color: "var(--text-faint)" }}>{(tasks || []).length} tasks</span>
      </div>

      <div style={{ display: "flex", gap: 6, flex: 1, overflowX: "auto", alignItems: "flex-start", paddingBottom: 8 }}>
        {statuses.map((st) => {
          const colTasks = (tasks || []).filter((x) => x.status === st);
          return (
            <div
              key={st}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => handleDrop(e, st)}
              style={{
                minWidth: 240,
                width: 240,
                flexShrink: 0,
                border: "1px solid var(--border)",
                borderRadius: 6,
                background: "var(--bg-surface)",
                display: "flex",
                flexDirection: "column",
                maxHeight: "calc(100vh - 96px)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "6px 8px", borderBottom: "1px solid var(--border)", background: "var(--bg-elevated)", borderRadius: "6px 6px 0 0" }}>
                <span style={{ width: 8, height: 8, borderRadius: 99, background: statusColor[st] }} />
                <span style={{ fontSize: 11, fontWeight: 600 }}>{t(st)}</span>
                <span style={{ fontSize: 10, color: "var(--text-faint)", background: "var(--bg)", padding: "1px 5px", borderRadius: 99, border: "1px solid var(--border)" }}>{colTasks.length}</span>
              </div>
              <div style={{ flex: 1, overflow: "auto", padding: 6, display: "flex", flexDirection: "column", gap: 4 }}>
                {colTasks.map((task) => (
                  <div
                    key={task.id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, task)}
                    style={{
                      border: "1px solid var(--border)",
                      borderRadius: 4,
                      padding: "6px 8px",
                      background: "var(--bg)",
                      cursor: "grab",
                      display: "flex",
                      flexDirection: "column",
                      gap: 3,
                    }}
                  >
                    <div style={{ fontSize: 11, color: "var(--text)", lineHeight: 1.35, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{task.title}</div>
                    <div style={{ display: "flex", gap: 4, fontSize: 10, color: "var(--text-faint)" }}>
                      {task.priority !== "none" && <span style={{ color: task.priority === "high" ? "#ef4444" : task.priority === "medium" ? "#f97316" : "#3b82f6" }}>{t(task.priority)}</span>}
                      {task.assignee && <span>{task.assignee}</span>}
                      {task.due_date && <span>{task.due_date}</span>}
                    </div>
                  </div>
                ))}
                {colTasks.length === 0 && <div style={{ fontSize: 11, color: "var(--text-faint)", textAlign: "center", padding: 12 }}>{t("noTasks")}</div>}
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ fontSize: 10, color: "var(--text-faint)" }}>Drag cards between columns to change status.</div>
    </div>
  );
}
