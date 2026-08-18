import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchEvents, fetchBoards, Event, Board } from "../api";
import { useI18n } from "../i18n";

const ACTION_LABEL: Record<string, string> = {
  create: "Created",
  update: "Updated",
  complete: "Completed",
  reopen: "Reopened",
  move: "Moved",
  delete: "Deleted",
};

const ACTION_COLOR: Record<string, string> = {
  create: "#22c55e",
  update: "#3b82f6",
  complete: "#22c55e",
  reopen: "#eab308",
  move: "#a855f7",
  delete: "#ef4444",
};

function timeAgo(iso: string): string {
  const then = new Date(iso + "Z");
  const now = new Date();
  const s = Math.floor((now.getTime() - then.getTime()) / 1000);
  if (s < 60) return "just now";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

export default function HistoryView() {
  const { t } = useI18n();
  const [filter, setFilter] = useState<"all" | "task" | "board">("all");

  const { data: events, isLoading } = useQuery({
    queryKey: ["events", filter],
    queryFn: () => fetchEvents({ entity_type: filter === "all" ? undefined : filter, limit: 500 }),
  });
  const { data: boards } = useQuery({ queryKey: ["boards"], queryFn: () => fetchBoards() });

  const boardName = useMemo(() => {
    const m = new Map<string, string>();
    (boards || []).forEach((b: Board) => m.set(b.id, b.name));
    return m;
  }, [boards]);

  if (isLoading) return <div style={{ padding: 16, fontSize: 11, color: "var(--text-muted)" }}>Loading...</div>;

  const list = events || [];

  return (
    <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 8, maxWidth: 860, margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 11, fontWeight: 700 }}>{t("history")}</span>
        <div style={{ flex: 1 }} />
        <div style={{ display: "flex", gap: 2 }}>
          {(["all", "task", "board"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                fontSize: 10,
                padding: "2px 8px",
                border: "1px solid var(--border)",
                borderRadius: 4,
                background: filter === f ? "var(--bg-elevated)" : "transparent",
                color: filter === f ? "var(--text)" : "var(--text-muted)",
                cursor: "pointer",
              }}
            >
              {f === "all" ? t("all") : f === "task" ? t("tasks") : t("boards")}
            </button>
          ))}
        </div>
      </div>

      {list.length === 0 ? (
        <div style={{ padding: 24, fontSize: 11, color: "var(--text-faint)", textAlign: "center" }}>{t("noHistory")}</div>
      ) : (
        <div style={{ border: "1px solid var(--border)", borderRadius: 6, background: "var(--bg-surface)", overflow: "hidden" }}>
          {list.map((e: Event) => {
            const label = ACTION_LABEL[e.action] || e.action;
            const color = ACTION_COLOR[e.action] || "var(--text-muted)";
            const boardLabel = boardName.get(e.entity_id) || "";
            return (
              <div
                key={e.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "4px 10px",
                  borderBottom: "1px solid var(--border)",
                  fontSize: 11,
                }}
              >
                <span style={{ width: 74, flexShrink: 0, color, fontWeight: 600, fontSize: 10 }}>{label}</span>
                <span style={{ color: "var(--text-muted)", fontSize: 10, flexShrink: 0 }}>{e.entity_type}</span>
                <span style={{ color: "var(--text)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {e.new_value || e.old_value || (boardLabel ? boardLabel : e.entity_id.slice(0, 8))}
                </span>
                {e.user_name && (
                  <span style={{ color: "var(--text-muted)", fontSize: 10, flexShrink: 0, background: "var(--bg)", padding: "1px 6px", borderRadius: 99, border: "1px solid var(--border)" }}>
                    by {e.user_name}
                  </span>
                )}
                <span style={{ color: "var(--text-faint)", fontSize: 10, flexShrink: 0 }}>{timeAgo(e.created_at)}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
