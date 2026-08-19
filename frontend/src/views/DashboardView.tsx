import { useQuery } from "@tanstack/react-query";
import { fetchBoardTree, fetchStats, fetchTasks, BoardTreeNode } from "../api";
import { useI18n } from "../i18n";
import { useWorkspace } from "../workspace";

function Bar({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const pct = total ? (value / total) * 100 : 0;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11 }}>
      <span style={{ width: 90, color: "var(--text-muted)", textAlign: "right", flexShrink: 0 }}>{label}</span>
      <div style={{ flex: 1, height: 14, background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, transition: "width 300ms" }} />
      </div>
      <span style={{ width: 44, textAlign: "right", color: "var(--text)", fontWeight: 600 }}>{value}</span>
      <span style={{ width: 36, color: "var(--text-faint)", fontSize: 10 }}>{pct.toFixed(0)}%</span>
    </div>
  );
}

function SectionBars({ sections, tasksPerSection }: { sections: BoardTreeNode[]; tasksPerSection: Map<string, number> }) {
  const total = Array.from(tasksPerSection.values()).reduce((a, b) => a + b, 0) || 1;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {sections.map((s) => (
        <Bar key={s.id} label={s.name} value={tasksPerSection.get(s.id) || 0} total={total} color={s.color} />
      ))}
    </div>
  );
}

export default function DashboardView() {
  const { t } = useI18n();
  const { currentId: wsId } = useWorkspace();
  const { data: stats } = useQuery({ queryKey: ["stats", wsId], queryFn: () => fetchStats(wsId || undefined) });
  const { data: tree } = useQuery({ queryKey: ["boards", "tree", wsId], queryFn: () => fetchBoardTree(wsId || undefined) });
  const { data: tasks } = useQuery({ queryKey: ["tasks", "all", wsId], queryFn: () => fetchTasks({ sort: "position", workspace_id: wsId || undefined }) });

  // per-section counts: for each top-level section, count tasks whose board is in its subtree
  const tasksPerSection = (() => {
    const m = new Map<string, number>();
    if (!tree || !tasks) return m;
    // build descendant sets
    const desc: Map<string, Set<string>> = new Map();
    const collect = (node: BoardTreeNode): Set<string> => {
      const s = new Set<string>([node.id]);
      node.children.forEach((c) => collect(c).forEach((x) => s.add(x)));
      desc.set(node.id, s);
      return s;
    };
    (tree as BoardTreeNode[]).forEach((sec) => collect(sec));
    // map board->section
    for (const sec of tree as BoardTreeNode[]) {
      const set = desc.get(sec.id)!;
      let count = 0;
      for (const task of tasks as never[] as { board_id: string }[]) if (set.has(task.board_id)) count++;
      m.set(sec.id, count);
    }
    return m;
  })();

  if (!stats) return <div style={{ padding: 16, fontSize: 11, color: "var(--text-muted)" }}>Loading...</div>;

  const total = stats.total || 1;

  return (
    <div style={{ padding: 12, display: "flex", flexDirection: "column", gap: 16, maxWidth: 720, margin: "0 auto" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
        {[
          { label: t("total"), value: stats.total, color: "var(--text)" },
          { label: t("in_progress"), value: stats.in_progress, color: "#3b82f6" },
          { label: t("waiting"), value: stats.waiting, color: "#eab308" },
          { label: t("done"), value: stats.done, color: "#22c55e" },
        ].map((k) => (
          <div key={k.label} style={{ border: "1px solid var(--border)", borderRadius: 6, padding: "10px 12px", background: "var(--bg-surface)", textAlign: "center" }}>
            <div style={{ fontSize: 10, color: "var(--text-muted)", letterSpacing: 0.4 }}>{k.label}</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: k.color, marginTop: 2 }}>{k.value}</div>
          </div>
        ))}
      </div>

      <div style={{ border: "1px solid var(--border)", borderRadius: 6, background: "var(--bg-surface)", padding: 12, display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 11, fontWeight: 700 }}>{t("completionRate")}</span>
          <span style={{ fontSize: 11, color: "var(--text-faint)" }}>{stats.completion_rate}%</span>
        </div>
        <div style={{ height: 14, background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 99, overflow: "hidden" }}>
          <div style={{ width: `${stats.completion_rate}%`, height: "100%", background: "#22c55e" }} />
        </div>
        <div style={{ display: "flex", gap: 12, fontSize: 10, color: "var(--text-faint)" }}>
          <span>{stats.done} done</span>
          <span>{stats.not_started} not started</span>
          <span>{stats.in_progress} in progress</span>
          <span>{stats.waiting} waiting</span>
        </div>
      </div>

      <div style={{ border: "1px solid var(--border)", borderRadius: 6, background: "var(--bg-surface)", padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ fontSize: 11, fontWeight: 700 }}>{t("tasksPerStatus")}</div>
        <Bar label={t("not_started")} value={stats.not_started} total={total} color="#6b7280" />
        <Bar label={t("in_progress")} value={stats.in_progress} total={total} color="#3b82f6" />
        <Bar label={t("waiting")} value={stats.waiting} total={total} color="#eab308" />
        <Bar label={t("done")} value={stats.done} total={total} color="#22c55e" />
      </div>

      <div style={{ border: "1px solid var(--border)", borderRadius: 6, background: "var(--bg-surface)", padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ fontSize: 11, fontWeight: 700 }}>{t("tasksPerPriority")}</div>
        {tasks &&
          (() => {
            const counts: Record<string, number> = { high: 0, medium: 0, low: 0, none: 0 };
            (tasks as { priority: string }[]).forEach((x) => { counts[x.priority] = (counts[x.priority] || 0) + 1; });
            const tot = (tasks as unknown[]).length || 1;
            return (
              <>
                <Bar label={t("high")} value={counts.high} total={tot} color="#ef4444" />
                <Bar label={t("medium")} value={counts.medium} total={tot} color="#f97316" />
                <Bar label={t("low")} value={counts.low} total={tot} color="#3b82f6" />
                <Bar label={t("none")} value={counts.none} total={tot} color="#6b7280" />
              </>
            );
          })()}
      </div>

      <div style={{ border: "1px solid var(--border)", borderRadius: 6, background: "var(--bg-surface)", padding: 12, display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ fontSize: 11, fontWeight: 700 }}>{t("tasksPerSection")}</div>
        {tree ? <SectionBars sections={tree as BoardTreeNode[]} tasksPerSection={tasksPerSection} /> : <span style={{ fontSize: 11, color: "var(--text-faint)" }}>Loading...</span>}
      </div>
    </div>
  );
}
