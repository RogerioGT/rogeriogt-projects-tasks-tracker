import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { createColumnHelper, flexRender, getCoreRowModel, getSortedRowModel, SortingState, useReactTable } from "@tanstack/react-table";
import { fetchBoards, fetchTasks, toggleComplete, Task } from "../api";
import { useI18n } from "../i18n";

const priorityColor: Record<string, string> = { high: "#ef4444", medium: "#f97316", low: "#3b82f6", none: "#6b7280" };

export default function ListView({ search }: { search: string }) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [sorting, setSorting] = useState<SortingState>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [assigneeFilter, setAssigneeFilter] = useState("");

  const { data: boards } = useQuery({ queryKey: ["boards", "flat"], queryFn: fetchBoards });
  const boardName = useMemo(() => {
    const m = new Map<string, string>();
    (boards || []).forEach((b) => m.set(b.id, b.name));
    return m;
  }, [boards]);

  const { data: tasks } = useQuery({
    queryKey: ["tasks", "list", search, statusFilter, priorityFilter, assigneeFilter],
    queryFn: () =>
      fetchTasks({
        search: search || undefined,
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        assignee: assigneeFilter || undefined,
        sort: "created_at",
      }),
  });

  const toggleMut = useMutation({
    mutationFn: (id: string) => toggleComplete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const rows = useMemo(() => tasks || [], [tasks]);

  const col = createColumnHelper<Task>();

  const columns = useMemo(
    () => [
      col.display({
        id: "check",
        header: "",
        size: 28,
        cell: (info) => (
          <input type="checkbox" checked={info.row.original.status === "done"} onChange={() => toggleMut.mutate(info.row.original.id)} style={{ accentColor: "#22c55e" }} />
        ),
      }),
      col.accessor("title", {
        header: t("title"),
        cell: (info) => (
          <span style={{ color: info.row.original.status === "done" ? "var(--text-faint)" : "var(--text)", textDecoration: info.row.original.status === "done" ? "line-through" : "none" }}>
            {info.getValue()}
          </span>
        ),
      }),
      col.accessor("status", {
        header: t("status"),
        cell: (info) => <span style={{ fontSize: 10, padding: "1px 5px", borderRadius: 3, background: "#6b728022", border: "1px solid var(--border)" }}>{t(info.getValue())}</span>,
      }),
      col.accessor("assignee", { header: t("assignee"), cell: (info) => info.getValue() || "—" }),
      col.accessor("due_date", { header: t("dueDate"), cell: (info) => info.getValue() || "—" }),
      col.accessor("priority", {
        header: t("priority"),
        cell: (info) => <span style={{ color: priorityColor[info.getValue()] || "#6b7280", fontWeight: 600 }}>{t(info.getValue())}</span>,
      }),
      col.accessor("tags", { header: t("tags"), cell: (info) => (info.getValue() || []).join(", ") || "—" }),
      col.display({
        id: "board",
        header: t("boardLabel"),
        cell: (info) => boardName.get(info.row.original.board_id) || info.row.original.board_id.slice(0, 6),
      }),
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [t, boardName],
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div style={{ padding: 8, display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={selStyle}>
          <option value="">{t("status")}: all</option>
          <option value="not_started">{t("not_started")}</option>
          <option value="in_progress">{t("in_progress")}</option>
          <option value="waiting">{t("waiting")}</option>
          <option value="done">{t("done")}</option>
        </select>
        <select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)} style={selStyle}>
          <option value="">{t("priority")}: all</option>
          <option value="high">{t("high")}</option>
          <option value="medium">{t("medium")}</option>
          <option value="low">{t("low")}</option>
          <option value="none">{t("none")}</option>
        </select>
        <input value={assigneeFilter} onChange={(e) => setAssigneeFilter(e.target.value)} placeholder={t("assignee")} style={inpStyle} />
        <span style={{ fontSize: 10, color: "var(--text-faint)" }}>{rows.length} tasks</span>
      </div>

      <div style={{ border: "1px solid var(--border)", borderRadius: 6, overflow: "auto", background: "var(--bg-surface)" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} style={{ background: "var(--bg-elevated)", borderBottom: "1px solid var(--border)" }}>
                {hg.headers.map((h) => (
                  <th
                    key={h.id}
                    onClick={h.column.getToggleSortingHandler()}
                    style={{
                      textAlign: "left",
                      padding: "6px 8px",
                      fontWeight: 600,
                      color: "var(--text-muted)",
                      whiteSpace: "nowrap",
                      cursor: h.column.getCanSort() ? "pointer" : "default",
                      borderBottom: "1px solid var(--border)",
                      userSelect: "none",
                    }}
                  >
                    {h.isPlaceholder ? null : flexRender(h.column.columnDef.header, h.getContext())}
                    {{ asc: " ▴", desc: " ▾" }[h.column.getIsSorted() as string] ?? ""}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} style={{ borderBottom: "1px solid var(--border)" }}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} style={{ padding: "5px 8px", color: "var(--text)", borderBottom: "1px solid var(--border)" }}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={columns.length} style={{ padding: 16, textAlign: "center", color: "var(--text-faint)" }}>
                  {t("noTasks")}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const selStyle: React.CSSProperties = {
  fontSize: 11,
  padding: "4px 8px",
  border: "1px solid var(--border)",
  borderRadius: 4,
  background: "var(--bg-surface)",
  color: "var(--text)",
};
const inpStyle: React.CSSProperties = {
  fontSize: 11,
  padding: "4px 8px",
  border: "1px solid var(--border)",
  borderRadius: 4,
  background: "var(--bg-surface)",
  color: "var(--text)",
  width: 140,
};
