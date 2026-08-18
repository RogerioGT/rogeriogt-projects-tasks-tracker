import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchBoards, fetchStatuses, Board } from "../api";
import { useI18n } from "../i18n";

export type Filters = {
  company: string; // board id of a company, "" = all
  project: string; // board id of a project, "" = all
  status: string;
  priority: string;
  assignee: string;
};

export const EMPTY_FILTERS: Filters = { company: "", project: "", status: "", priority: "", assignee: "" };

const selStyle: React.CSSProperties = {
  fontSize: 11,
  padding: "4px 8px",
  border: "1px solid var(--border)",
  borderRadius: 4,
  background: "var(--bg-surface)",
  color: "var(--text)",
};
const inpStyle: React.CSSProperties = { ...selStyle, width: 130 };

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
  const { data: boards } = useQuery({ queryKey: ["boards", "flat"], queryFn: fetchBoards });
  const { data: statuses } = useQuery({ queryKey: ["statuses"], queryFn: fetchStatuses });

  const { companies, projectsByCompany } = useMemo(() => {
    const all = (boards || []) as Board[];
    const companies = all.filter((b) => b.kind === "company");
    const projectsByCompany = new Map<string, Board[]>();
    for (const b of all) {
      if (b.kind === "project" && b.parent_id) {
        const list = projectsByCompany.get(b.parent_id) || [];
        list.push(b);
        projectsByCompany.set(b.parent_id, list);
      }
    }
    return { companies, projectsByCompany };
  }, [boards]);

  const projects = filters.company ? projectsByCompany.get(filters.company) || [] : [];

  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch });

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
            {companies.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
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
    </div>
  );
}

/** Build the backend query params for the current filter selection. */
export function filtersToQuery(filters: Filters) {
  const params: { board_id?: string; include_descendants?: boolean; status?: string; priority?: string; assignee?: string } = {};
  if (filters.project) {
    params.board_id = filters.project;
  } else if (filters.company) {
    params.board_id = filters.company;
    params.include_descendants = true;
  }
  if (filters.status) params.status = filters.status;
  if (filters.priority) params.priority = filters.priority;
  if (filters.assignee) params.assignee = filters.assignee;
  return params;
}
