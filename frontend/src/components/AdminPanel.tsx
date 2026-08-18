import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchUsers,
  fetchTeams,
  adminCreateUser,
  adminUpdateUser,
  createTeam,
  renameTeam,
  deleteTeam,
  addTeamMember,
  removeTeamMember,
} from "../api";
import { useI18n } from "../i18n";

const inputStyle: React.CSSProperties = {
  fontSize: 11,
  padding: "5px 8px",
  border: "1px solid var(--border)",
  borderRadius: 4,
  background: "var(--bg)",
  color: "var(--text)",
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

export default function AdminPanel({ onClose }: { onClose: () => void }) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"users" | "teams">("users");
  const [error, setError] = useState("");

  const { data: users } = useQuery({ queryKey: ["users"], queryFn: fetchUsers });
  const { data: teams } = useQuery({ queryKey: ["teams"], queryFn: fetchTeams });

  // users form
  const [uEmail, setUEmail] = useState("");
  const [uName, setUName] = useState("");
  const [uPass, setUPass] = useState("");
  const [uAdmin, setUAdmin] = useState(false);
  const createUserMut = useMutation({
    mutationFn: () => adminCreateUser({ email: uEmail, name: uName, password: uPass, is_admin: uAdmin }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["users"] }); setUEmail(""); setUName(""); setUPass(""); setUAdmin(false); },
    onError: (e) => setError(e instanceof Error ? e.message : String(e)),
  });
  const updateUserMut = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Parameters<typeof adminUpdateUser>[1] }) => adminUpdateUser(id, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
    onError: (e) => setError(e instanceof Error ? e.message : String(e)),
  });

  // teams form
  const [teamName, setTeamName] = useState("");
  const createTeamMut = useMutation({
    mutationFn: () => createTeam(teamName),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["teams"] }); setTeamName(""); },
    onError: (e) => setError(e instanceof Error ? e.message : String(e)),
  });
  const deleteTeamMut = useMutation({
    mutationFn: (id: string) => deleteTeam(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teams"] }),
  });
  const addMemberMut = useMutation({
    mutationFn: ({ teamId, userId }: { teamId: string; userId: string }) => addTeamMember(teamId, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teams"] }),
    onError: (e) => setError(e instanceof Error ? e.message : String(e)),
  });
  const removeMemberMut = useMutation({
    mutationFn: ({ teamId, userId }: { teamId: string; userId: string }) => removeTeamMember(teamId, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teams"] }),
  });

  const userName = (id: string) => {
    const u = (users || []).find((x) => x.id === id);
    return u ? u.name || u.email : id.slice(0, 8);
  };

  return (
    <div onClick={(e) => e.stopPropagation()} style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8, padding: 16, minWidth: 480, maxWidth: 560, maxHeight: "80vh", overflow: "auto", display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 12, fontWeight: 700 }}>{t("settings")}</span>
        <div style={{ flex: 1 }} />
        <div style={{ display: "flex", gap: 2 }}>
          <button onClick={() => setTab("users")} style={{ ...btnStyle, background: tab === "users" ? "var(--bg)" : "transparent" }}>{t("people")}</button>
          <button onClick={() => setTab("teams")} style={{ ...btnStyle, background: tab === "teams" ? "var(--bg)" : "transparent" }}>{t("teams")}</button>
        </div>
      </div>

      {error && <div style={{ fontSize: 10, color: "#ef4444" }}>{error}</div>}

      {tab === "users" && (
        <>
          <div style={{ display: "flex", gap: 6 }}>
            <input value={uName} onChange={(e) => setUName(e.target.value)} placeholder={t("name")} style={{ ...inputStyle, flex: 1 }} />
            <input value={uEmail} onChange={(e) => setUEmail(e.target.value)} placeholder={t("email")} style={{ ...inputStyle, flex: 1.4 }} />
            <input type="password" value={uPass} onChange={(e) => setUPass(e.target.value)} placeholder={t("password")} style={{ ...inputStyle, flex: 1 }} />
            <label style={{ fontSize: 10, display: "flex", alignItems: "center", gap: 3, color: "var(--text-muted)", whiteSpace: "nowrap" }}>
              <input type="checkbox" checked={uAdmin} onChange={(e) => setUAdmin(e.target.checked)} /> {t("admin")}
            </label>
            <button onClick={() => createUserMut.mutate()} disabled={!uEmail || !uPass} style={{ ...btnStyle, background: "#3b82f6", color: "#fff", borderColor: "#3b82f6", opacity: uEmail && uPass ? 1 : 0.5 }}>{t("addUser")}</button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {(users || []).map((u) => (
              <div key={u.id} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, padding: "4px 6px", border: "1px solid var(--border)", borderRadius: 4 }}>
                <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {u.name || u.email} <span style={{ color: "var(--text-faint)" }}>({u.email})</span>
                </span>
                {u.is_admin && <span style={{ fontSize: 9, padding: "1px 5px", borderRadius: 99, background: "#8b5cf622", color: "#a78bfa", border: "1px solid #8b5cf655" }}>{t("admin")}</span>}
                <button onClick={() => updateUserMut.mutate({ id: u.id, patch: { is_admin: !u.is_admin } })} style={{ ...btnStyle, fontSize: 10, padding: "2px 6px" }}>
                  {u.is_admin ? t("member") : t("admin")}
                </button>
                <button
                  onClick={() => updateUserMut.mutate({ id: u.id, patch: { is_active: !u.is_active } })}
                  style={{ ...btnStyle, fontSize: 10, padding: "2px 6px", color: u.is_active ? "#ef4444" : "#22c55e", borderColor: u.is_active ? "#ef444455" : "#22c55e55" }}
                >
                  {u.is_active ? t("deactivate") : t("activate")}
                </button>
              </div>
            ))}
          </div>
        </>
      )}

      {tab === "teams" && (
        <>
          <div style={{ display: "flex", gap: 6 }}>
            <input value={teamName} onChange={(e) => setTeamName(e.target.value)} placeholder={t("teamName")} style={{ ...inputStyle, flex: 1 }} onKeyDown={(e) => { if (e.key === "Enter") createTeamMut.mutate(); }} />
            <button onClick={() => createTeamMut.mutate()} disabled={!teamName.trim()} style={{ ...btnStyle, background: "#3b82f6", color: "#fff", borderColor: "#3b82f6", opacity: teamName.trim() ? 1 : 0.5 }}>{t("createTeam")}</button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {(teams || []).map((team) => {
              const memberIds = new Set(team.members.map((m) => m.user_id));
              const candidates = (users || []).filter((u) => !memberIds.has(u.id));
              return (
                <div key={team.id} style={{ border: "1px solid var(--border)", borderRadius: 6, padding: 8, display: "flex", flexDirection: "column", gap: 6 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 11, fontWeight: 700, flex: 1 }}>{team.name}</span>
                    <span style={{ fontSize: 10, color: "var(--text-faint)" }}>{team.members.length} {t("members")}</span>
                    <button onClick={() => deleteTeamMut.mutate(team.id)} style={{ ...btnStyle, color: "#ef4444", borderColor: "#ef444455", fontSize: 10, padding: "2px 6px" }}>x</button>
                  </div>
                  <div style={{ display: "flex", gap: 6 }}>
                    <select
                      defaultValue=""
                      onChange={(e) => { if (e.target.value) addMemberMut.mutate({ teamId: team.id, userId: e.target.value }); }}
                      style={{ ...inputStyle, flex: 1 }}
                    >
                      <option value="">{t("addUser")}...</option>
                      {candidates.map((u) => (
                        <option key={u.id} value={u.id}>{u.name || u.email}</option>
                      ))}
                    </select>
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {team.members.map((m) => (
                      <span key={m.id} style={{ fontSize: 10, padding: "2px 8px", borderRadius: 99, background: "var(--bg)", border: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 5 }}>
                        {userName(m.user_id)}
                        <button onClick={() => removeMemberMut.mutate({ teamId: team.id, userId: m.user_id })} style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: 0, fontSize: 10 }}>x</button>
                      </span>
                    ))}
                    {team.members.length === 0 && <span style={{ fontSize: 10, color: "var(--text-faint)" }}>{t("noTasks")}</span>}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button onClick={onClose} style={btnStyle}>{t("close")}</button>
      </div>
    </div>
  );
}
