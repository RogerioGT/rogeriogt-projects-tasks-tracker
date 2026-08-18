import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchUsers, fetchAcl, shareBoard, unshareBoard } from "../api";
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

export default function ShareDialog({ boardId, boardName, onClose }: { boardId: string; boardName: string; onClose: () => void }) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [selectedUser, setSelectedUser] = useState("");
  const [permission, setPermission] = useState<"view" | "edit">("edit");

  const { data: users } = useQuery({ queryKey: ["users"], queryFn: fetchUsers });
  const { data: acl } = useQuery({ queryKey: ["acl", boardId], queryFn: () => fetchAcl(boardId) });

  const shareMut = useMutation({
    mutationFn: () => shareBoard(boardId, { user_id: selectedUser, permission }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["acl", boardId] }); setSelectedUser(""); },
  });
  const unshareMut = useMutation({
    mutationFn: (userId: string) => unshareBoard(boardId, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["acl", boardId] }),
  });

  const sharedIds = new Set((acl || []).map((s) => s.user_id));
  const aclByUser = new Map((acl || []).map((s) => [s.user_id, s.permission]));
  const shareable = (users || []).filter((u) => !sharedIds.has(u.id));

  return (
    <div onClick={(e) => e.stopPropagation()} style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8, padding: 16, minWidth: 320, display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ fontSize: 12, fontWeight: 700 }}>{t("share")}: {boardName}</div>

      <div style={{ display: "flex", gap: 6 }}>
        <select value={selectedUser} onChange={(e) => setSelectedUser(e.target.value)} style={inputStyle}>
          <option value="">{t("selectUser")}</option>
          {shareable.map((u) => (
            <option key={u.id} value={u.id}>{u.name || u.email}</option>
          ))}
        </select>
        <select value={permission} onChange={(e) => setPermission(e.target.value as "view" | "edit")} style={{ ...inputStyle, width: 90 }}>
          <option value="edit">{t("edit")}</option>
          <option value="view">{t("view")}</option>
        </select>
      </div>
      <button
        onClick={() => selectedUser && shareMut.mutate()}
        disabled={!selectedUser}
        style={{ ...btnStyle, background: "#3b82f6", color: "#fff", borderColor: "#3b82f6", opacity: selectedUser ? 1 : 0.5 }}
      >
        {t("share")}
      </button>

      {(acl || []).length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 4 }}>
          <div style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 600 }}>{t("sharedWith")}</div>
          {(acl || []).map((s) => {
            const u = (users || []).find((x) => x.id === s.user_id);
            return (
              <div key={s.id} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11 }}>
                <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{u?.name || u?.email || s.user_id.slice(0, 8)}</span>
                <span style={{ color: "var(--text-faint)", fontSize: 10 }}>{t(s.permission === "edit" ? "edit" : "view")}</span>
                <button onClick={() => unshareMut.mutate(s.user_id)} style={{ ...btnStyle, color: "#ef4444", borderColor: "#ef444455", fontSize: 10, padding: "2px 6px" }}>x</button>
              </div>
            );
          })}
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 4 }}>
        <button onClick={onClose} style={btnStyle}>{t("close")}</button>
      </div>
    </div>
  );
}
