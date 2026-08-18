import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchBoardTree, fetchStatuses, BoardTreeNode } from "../api";
import { useI18n } from "../i18n";

export type Filters = {
  company: string; // board id of a scope (section/company/any board with children), "" = all
  project: string; // board id of a board inside the scope, "" = all in scope
  status: string;
  priority: string;
  assignee: string;
  sort: string; // position | created_at | due_date | title | priority | status
};

export const EMPTY_FILTERS: Filters = { company: "", project: "", status: "", priority: "", assignee: "", sort: "position" };

const selStyle: React.CSSProperties = {
  fontSize: 11,
  padding: "4px 8px",
  border: "1px solid var(--border)",
  borderRadius: 4,
  background: "var(--bg-surface)",
  color: "var(--text)",
  maxWidth: 200,
};
const inpStyle: React.CSSProperties = { ...selStyle, width: 130 };

/** Flatten the board tree into a list with depth + parent chain, in display order. */
function flattenTree(nodes: BoardTreeNode[], depth = 0): { node: BoardTreeNode; depth: number }[] {
  const out: { node: BoardTreeNode; depth: number }[] = [];
  for (const n of nodes) {
    out.push({ node: n, depth });
    out.push(...flattenTree(n.children, depth + 1));
  }
  return out;
}

/** Collect every board id in the subtree of `node` (any depth). */
function collectIds(node: BoardTreeNode): string[] {
  const ids: string[] = [];
  const walk = (n: BoardTreeNode) => {
    for (const c of n.children) {
      ids.push(c.id);
      walk(c);
    }
  };
  walk(node);
  return ids;
}

export default function FilterBar({
  filters,
  onChange,
  showBoardScope = true,
}: {
  filters: Filters;
  onChange: (f: Filters) => void;
  showBoardScope?: boolean;
}) {
  const { t } = useI18n();
  const { data: tree } = useQuery({ queryKey: ["boards", "tree"], queryFn: fetchBoardTree });
  const { data: statuses } = useQuery({ queryKey: ["statuses"], queryFn: fetchStatuses });

  const { scopes, projectsFor } = useMemo(() => {
    const flat = flattenTree(tree || []);
    // Scopes: sections, companies, and any board that contains sub-boards.
    const scopes = flat.filter(({ node }) => node.kind === "section" || node.kind === "company" || node.children.length > 0);
    const byId = new Map(flat.map(({ node }) => [node.id, node]));
    const projectsFor = (scopeId: string) => {
      const scope = byId.get(scopeId);
      if (!scope) return [];
      const ids = collectIds(scope);
      return ids
        .map((id) => byId.get(id))
        .filter((n): n is BoardTreeNode => !!n)
        .map((n) => ({ id: n.id, name: n.name, kind: n.kind }));
    };
    return { scopes, projectsFor };
  }, [tree]);

  const projects = filters.company ? projectsFor(filters.company) : [];

  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch });
  const indent = (d: number) => "\u00A0".repeat(d * 2);

  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
      {showBoardScope && (
        <>
          <select
            value={filters.company}
            onChange={(e) => set({ company: e.target.value, project: "" })}
            style={selStyle}
          >
            <option value="">{t("company")}: {t("all")}</option>
            {scopes.map(({ node, depth }) => (
              <option key={node.id} value={node.id}>{indent(depth)}{node.name}</option>
            ))}
          </select>
          <select
            value={filters.project}
            onChange={(e) => set({ project: e.target.value })}
            style={selStyle}
            disabled={!filters.company}
          >
            <option value="">{t("project")}: {t("all")}</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </>
      )}
      <select value={filters.status} onChange={(e) => set({ status: e.target.value })} style={selStyle}>
        <option value="">{t("status")}: {t("all")}</option>
        {(statuses || []).map((s) => (
          <option key={s.name} value={s.name}>{t(s.name)}</option>
        ))}
      </select>
      <select value={filters.priority} onChange={(e) => set({ priority: e.target.value })} style={selStyle}>
        <option value="">{t("priority")}: {t("all")}</option>
        <option value="high">{t("high")}</option>
        <option value="medium">{t("medium")}</option>
        <option value="low">{t("low")}</option>
        <option value="none">{t("none")}</option>
      </select>
      <input
        value={filters.assignee}
        onChange={(e) => set({ assignee: e.target.value })}
        placeholder={t("assignee")}
        style={inpStyle}
      />
      <select value={filters.sort} onChange={(e) => set({ sort: e.target.value })} style={selStyle}>
        <option value="position">{t("sortBy")}: {t("manual")}</option>
        <option value="created_at">{t("sortBy")}: {t("newestFirst")}</option>
        <option value="due_date">{t("sortBy")}: {t("dueDate")}</option>
        <option value="title">{t("sortBy")}: {t("title")}</option>
        <option value="priority">{t("sortBy")}: {t("priority")}</option>
        <option value="status">{t("sortBy")}: {t("status")}</option>
      </select>
    </div>
  );
}

/** Build the backend query params for the current filter selection. */
export function filtersToQuery(filters: Filters) {
  const params: { board_id?: string; include_descendants?: boolean; status?: string; priority?: string; assignee?: string; sort?: string } = {};
  if (filters.project) {
    // include descendants so sub-projects under the selected project are included too
    params.board_id = filters.project;
    params.include_descendants = true;
  } else if (filters.company) {
    params.board_id = filters.company;
    params.include_descendants = true;
  }
  if (filters.status) params.status = filters.status;
  if (filters.priority) params.priority = filters.priority;
  if (filters.assignee) params.assignee = filters.assignee;
  if (filters.sort) params.sort = filters.sort;
  return params;
}
