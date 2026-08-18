import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchUsers,
  fetchTeams,
  fetchAcl,
  fetchTaskAcl,
  shareBoard,
  shareTask,
  shareTasksBatch,
  unshareBoard,
  unshareTask,
} from "../api";
import { useI18n } from "../i18n";

const inputStyle: React.CSSProperties = {
  fontSize: 11,
  padding: "5px 8px",
  border: "1px solid var(--border)",
  borderRadius: 4,
  background: "var(--bg)",
  color: "var(--text)",
  width: "100%",
  boxSizing: "border-box",
};
const btnStyle: React.CSSProperties = {
  fontSize: 11,
  padding: "4px 8px",
  border: "1px solid var(--border)",
  borderRadius: 4,
  background: "var(--bg-elevated)",
  color: "var(--text)",
  cursor: "pointer",
};

type Scope =
  | { type: "board"; boardId: string; boardName: string }
  | { type: "task"; taskIds: string[]; label: string };

export default function ShareDialog({ scope, onClose }: { scope: Scope; onClose: () => void }) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [targetType, setTargetType] = useState<"user" | "team">("user");
  const [selectedUser, setSelectedUser] = useState("");
  const [selectedTeam, setSelectedTeam] = useState("");
  const [permission, setPermission] = useState<"view" | "edit">("edit");

  const { data: users } = useQuery({ queryKey: ["users"], queryFn: fetchUsers });
  const { data: teams } = useQuery({ queryKey: ["teams"], queryFn: fetchTeams });

  const isBoard = scope.type === "board";
  const boardId = isBoard ? scope.boardId : "";
  const { data: acl } = useQuery({
    queryKey: ["acl", boardId],
    queryFn: () => fetchAcl(boardId),
    enabled: isBoard,
  });
  const taskId = !isBoard && scope.taskIds.length === 1 ? scope.taskIds[0] : "";
  const { data: taskAcl } = useQuery({
    queryKey: ["task-acl", taskId],
    queryFn: () => fetchTaskAcl(taskId),
    enabled: !!taskId,
  });

  const shareMut = useMutation({
    mutationFn: (): Promise<unknown> => {
      const target = targetType === "user"
        ? { user_id: selectedUser || null, team_id: null }
        : { user_id: null, team_id: selectedTeam || null };
      if (isBoard) return shareBoard(scope.boardId, { ...target, permission });
      if (scope.taskIds.length === 1) return shareTask(scope.taskIds[0], { ...target, permission });
      return shareTasksBatch(scope.taskIds, { ...target, permission });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["acl"] });
      qc.invalidateQueries({ queryKey: ["task-acl"] });
      setSelectedUser("");
      setSelectedTeam("");
    },
  });

  const unshareMut = useMutation({
    mutationFn: ({ aclId }: { aclId: string }): Promise<unknown> => {
      if (isBoard) return unshareBoard(scope.boardId, aclId);
      return unshareTask(taskId, aclId);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["acl"] });
      qc.invalidateQueries({ queryKey: ["task-acl"] });
    },
  });

  const targetSelected = targetType === "user" ? !!selectedUser : !!selectedTeam;
  const targetName = (userId: string | null, teamId: string | null) => {
    if (userId) {
      const u = (users || []).find((x) => x.id === userId);
      return u?.name || u?.email || userId.slice(0, 8);
    }
    if (teamId) {
      const team = (teams || []).find((x) => x.id === teamId);
      return team?.name || teamId.slice(0, 8);
    }
    return "";
  };

  const shares = isBoard ? (acl || []) : (taskAcl || []);

  return (
    <div onClick={(e) => e.stopPropagation()} style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8, padding: 16, minWidth: 340, maxWidth: 420, display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ fontSize: 12, fontWeight: 700 }}>
        {isBoard ? `${t("share")}: ${scope.boardName}` : scope.taskIds.length > 1 ? `${t("shareSelected")} (${scope.taskIds.length})` : `${t("shareTask")}`}
      </div>

      <div style={{ display: "flex", gap: 6 }}>
        <select value={targetType} onChange={(e) => setTargetType(e.target.value as "user" | "team")} style={{ ...inputStyle, width: 100 }}>
          <option value="user">{t("person")}</option>
          <option value="team">{t("team")}</option>
        </select>
        {targetType === "user" ? (
          <select value={selectedUser} onChange={(e) => setSelectedUser(e.target.value)} style={inputStyle}>
            <option value="">{t("selectUser")}</option>
            {(users || []).map((u) => (
              <option key={u.id} value={u.id}>{u.name || u.email}</option>
            ))}
          </select>
        ) : (
          <select value={selectedTeam} onChange={(e) => setSelectedTeam(e.target.value)} style={inputStyle}>
            <option value="">{t("teams")}</option>
            {(teams || []).map((team) => (
              <option key={team.id} value={team.id}>{team.name} ({team.members.length})</option>
            ))}
          </select>
        )}
        <select value={permission} onChange={(e) => setPermission(e.target.value as "view" | "edit")} style={{ ...inputStyle, width: 90 }}>
          <option value="edit">{t("edit")}</option>
          <option value="view">{t("view")}</option>
        </select>
      </div>
      <button
        onClick={() => shareMut.mutate()}
        disabled={!targetSelected}
        style={{ ...btnStyle, background: "#3b82f6", color: "#fff", borderColor: "#3b82f6", opacity: targetSelected ? 1 : 0.5 }}
      >
        {t("share")}
      </button>

      {shares.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 4 }}>
          <div style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 600 }}>{t("sharedWith")}</div>
          {shares.map((s: { id: string; user_id: string | null; team_id: string | null; permission: string }) => (
            <div key={s.id} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11 }}>
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {s.team_id ? "👥 " : ""}{targetName(s.user_id, s.team_id)}
              </span>
              <span style={{ color: "var(--text-faint)", fontSize: 10 }}>{t(s.permission)}</span>
              <button onClick={() => unshareMut.mutate({ aclId: s.id })} style={{ ...btnStyle, color: "#ef4444", borderColor: "#ef444455", fontSize: 10, padding: "2px 6px" }}>x</button>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 4 }}>
        <button onClick={onClose} style={btnStyle}>{t("close")}</button>
      </div>
    </div>
  );
}
