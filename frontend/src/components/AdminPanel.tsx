import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchUsers,
  fetchTeams,
  fetchStatuses,
  fetchTrash,
  restoreBoard,
  restoreTask,
  purgeBoard,
  purgeTask,
  restoreWorkspace,
  purgeWorkspace,
  createStatus,
  updateStatus,
  deleteStatus,
  adminCreateUser,
  adminUpdateUser,
  createTeam,
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

type Tab = "users" | "teams" | "statuses" | "trash";

function friendlyError(e: unknown): string {
  const m = e instanceof Error ? e.message : String(e);
  // API errors arrive as "HTTP <code>: {...}" or plain "{...}". Extract detail.
  const jsonMatch = m.match(/\{.*\}/s);
  if (jsonMatch) {
    try {
      const parsed = JSON.parse(jsonMatch[0]);
      if (parsed && parsed.detail) {
        return typeof parsed.detail === "string" ? parsed.detail : JSON.stringify(parsed.detail);
      }
    } catch {
      /* not json */
    }
  }
  return m;
}

export default function AdminPanel({ onClose }: { onClose: () => void }) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("users");
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  const { data: users } = useQuery({ queryKey: ["users"], queryFn: fetchUsers });
  const { data: teams } = useQuery({ queryKey: ["teams"], queryFn: fetchTeams });
  const { data: statuses } = useQuery({ queryKey: ["statuses"], queryFn: fetchStatuses });

  const flash = (message: string, isError = false) => {
    if (isError) setError(message);
    else setMsg(message);
    setTimeout(() => { setError(""); setMsg(""); }, 4000);
  };

  // users form
  const [uEmail, setUEmail] = useState("");
  const [uName, setUName] = useState("");
  const [uPass, setUPass] = useState("");
  const [uAdmin, setUAdmin] = useState(false);
  const [editUser, setEditUser] = useState<{ id: string; name: string; email: string; phone: string } | null>(null);
  const createUserMut = useMutation({
    mutationFn: () => adminCreateUser({ email: uEmail, name: uName, password: uPass, is_admin: uAdmin }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["users"] }); setUEmail(""); setUName(""); setUPass(""); setUAdmin(false); flash(t("saved")); },
    onError: (e) => flash(friendlyError(e), true),
  });
  const updateUserMut = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Parameters<typeof adminUpdateUser>[1] }) => adminUpdateUser(id, patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
    onError: (e) => flash(friendlyError(e), true),
  });

  // teams
  const [teamName, setTeamName] = useState("");
  const createTeamMut = useMutation({
    mutationFn: () => createTeam(teamName),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["teams"] }); setTeamName(""); flash(t("saved")); },
    onError: (e) => flash(friendlyError(e), true),
  });
  const deleteTeamMut = useMutation({
    mutationFn: (id: string) => deleteTeam(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["teams"] }); flash(t("saved")); },
    onError: (e) => flash(friendlyError(e), true),
  });
  const addMemberMut = useMutation({
    mutationFn: ({ teamId, userId }: { teamId: string; userId: string }) => addTeamMember(teamId, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teams"] }),
    onError: (e) => flash(friendlyError(e), true),
  });
  const removeMemberMut = useMutation({
    mutationFn: ({ teamId, userId }: { teamId: string; userId: string }) => removeTeamMember(teamId, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teams"] }),
    onError: (e) => flash(friendlyError(e), true),
  });

  // statuses
  const [statusName, setStatusName] = useState("");
  const [statusColor, setStatusColor] = useState("#64748b");
  const createStatusMut = useMutation({
    mutationFn: () => createStatus({ name: statusName, color: statusColor }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["statuses"] }); setStatusName(""); flash(t("saved")); },
    onError: (e) => flash(friendlyError(e), true),
  });
  const deleteStatusMut = useMutation({
    mutationFn: (id: string) => deleteStatus(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["statuses"] }); flash(t("saved")); },
    onError: (e) => flash(friendlyError(e), true),
  });

  const userName = (id: string) => {
    const u = (users || []).find((x) => x.id === id);
    return u ? u.name || u.email : id.slice(0, 8);
  };

  return (
    <div onClick={(e) => e.stopPropagation()} style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8, padding: 16, width: "95vw", maxWidth: "95vw", maxHeight: "85vh", overflow: "auto", display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <span style={{ fontSize: 12, fontWeight: 700 }}>{t("settings")}</span>
        <div style={{ flex: 1 }} />
        <div style={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          <button onClick={() => setTab("users")} style={{ ...btnStyle, background: tab === "users" ? "var(--bg)" : "transparent" }}>{t("people")}</button>
          <button onClick={() => setTab("teams")} style={{ ...btnStyle, background: tab === "teams" ? "var(--bg)" : "transparent" }}>{t("teams")}</button>
          <button onClick={() => setTab("statuses")} style={{ ...btnStyle, background: tab === "statuses" ? "var(--bg)" : "transparent" }}>{t("statuses")}</button>
          <button onClick={() => setTab("trash")} style={{ ...btnStyle, background: tab === "trash" ? "var(--bg)" : "transparent" }}>{t("trash")}</button>
        </div>
      </div>

      {error && <div style={{ fontSize: 11, color: "#ef4444", border: "1px solid #ef444455", borderRadius: 4, padding: "6px 8px", background: "#ef444411" }}>{error}</div>}
      {msg && <div style={{ fontSize: 11, color: "#22c55e", border: "1px solid #22c55e55", borderRadius: 4, padding: "6px 8px", background: "#22c55e11" }}>{msg}</div>}

      {tab === "users" && (
        <>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <input value={uName} onChange={(e) => setUName(e.target.value)} placeholder={t("name")} style={{ ...inputStyle, flex: 1, minWidth: 120 }} />
            <input value={uEmail} onChange={(e) => setUEmail(e.target.value)} placeholder={t("email")} style={{ ...inputStyle, flex: 1.4, minWidth: 160 }} />
            <input type="password" value={uPass} onChange={(e) => setUPass(e.target.value)} placeholder={t("password")} style={{ ...inputStyle, flex: 1, minWidth: 120 }} />
            <label style={{ fontSize: 10, display: "flex", alignItems: "center", gap: 3, color: "var(--text-muted)", whiteSpace: "nowrap" }}>
              <input type="checkbox" checked={uAdmin} onChange={(e) => setUAdmin(e.target.checked)} /> {t("admin")}
            </label>
            <button onClick={() => createUserMut.mutate()} disabled={!uEmail || !uPass} style={{ ...btnStyle, background: "#3b82f6", color: "#fff", borderColor: "#3b82f6", opacity: uEmail && uPass ? 1 : 0.5 }}>{t("addUser")}</button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {(users || []).map((u) => (
              <div key={u.id} style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 11, padding: "4px 6px", border: "1px solid var(--border)", borderRadius: 4 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", minWidth: 150 }}>
                    {u.name || u.email} <span style={{ color: "var(--text-faint)" }}>({u.email})</span>
                    {u.phone ? <span style={{ color: "var(--text-faint)" }}> · {u.phone}</span> : null}
                  </span>
                  {u.is_admin && <span style={{ fontSize: 9, padding: "1px 5px", borderRadius: 99, background: "#8b5cf622", color: "#a78bfa", border: "1px solid #8b5cf655" }}>{t("admin")}</span>}
                  {!u.is_active && <span style={{ fontSize: 9, padding: "1px 5px", borderRadius: 99, background: "#ef444422", color: "#ef4444", border: "1px solid #ef444455" }}>{t("deactivated")}</span>}
                  <button onClick={() => setEditUser(editUser?.id === u.id ? null : { id: u.id, name: u.name, email: u.email, phone: u.phone || "" })} style={{ ...btnStyle, fontSize: 10, padding: "2px 6px" }}>✎ {t("edit")}</button>
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
                {editUser?.id === u.id && (
                  <UserEditor
                    key={u.id}
                    initial={{ name: u.name, email: u.email, phone: u.phone || "" }}
                    onSave={(patch) => { updateUserMut.mutate({ id: u.id, patch }); setEditUser(null); }}
                    onCancel={() => setEditUser(null)}
                    onPassword={(pwd) => updateUserMut.mutate({ id: u.id, patch: { password: pwd } })}
                  />
                )}
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
              const candidates = (users || []).filter((u) => !memberIds.has(u.id) && u.is_active);
              return (
                <div key={team.id} style={{ border: "1px solid var(--border)", borderRadius: 6, padding: 8, display: "flex", flexDirection: "column", gap: 6 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 11, fontWeight: 700, flex: 1 }}>{team.name}</span>
                    <span style={{ fontSize: 10, color: "var(--text-faint)" }}>{team.members.length} {t("members")}</span>
                    <button onClick={() => { if (confirm(t("deleteTeamWarning"))) deleteTeamMut.mutate(team.id); }} style={{ ...btnStyle, color: "#ef4444", borderColor: "#ef444455", fontSize: 10, padding: "2px 6px" }}>x</button>
                  </div>
                  {candidates.length > 0 ? (
                    <MemberSelect teamId={team.id} candidates={candidates} onAdd={(userId) => addMemberMut.mutate({ teamId: team.id, userId })} label={t("addUser")} />
                  ) : (
                    <span style={{ fontSize: 10, color: "var(--text-faint)" }}>{t("noUsersToAdd")}</span>
                  )}
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {team.members.map((m) => (
                      <span key={m.id} style={{ fontSize: 10, padding: "2px 8px", borderRadius: 99, background: "var(--bg)", border: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 5 }}>
                        {userName(m.user_id)}
                        <button onClick={() => { if (confirm(t("removeMemberWarning"))) removeMemberMut.mutate({ teamId: team.id, userId: m.user_id }); }} style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: 0, fontSize: 10 }}>x</button>
                      </span>
                    ))}
                    {team.members.length === 0 && <span style={{ fontSize: 10, color: "var(--text-faint)" }}>{t("noMembers")}</span>}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {tab === "statuses" && (
        <>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
            <input value={statusName} onChange={(e) => setStatusName(e.target.value)} placeholder={t("newStatusPlaceholder")} style={{ ...inputStyle, flex: 1, minWidth: 160 }} onKeyDown={(e) => { if (e.key === "Enter") createStatusMut.mutate(); }} />
            <input type="color" value={statusColor} onChange={(e) => setStatusColor(e.target.value)} style={{ width: 36, height: 27, padding: 0, border: "1px solid var(--border)", borderRadius: 4, background: "var(--bg)", cursor: "pointer" }} />
            <button onClick={() => createStatusMut.mutate()} disabled={!statusName.trim()} style={{ ...btnStyle, background: "#3b82f6", color: "#fff", borderColor: "#3b82f6", opacity: statusName.trim() ? 1 : 0.5 }}>{t("addStatus")}</button>
          </div>
          <div style={{ fontSize: 10, color: "var(--text-muted)" }}>{t("statusesHint")}</div>

          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {(statuses || []).map((s) => (
              <span key={s.id} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, padding: "4px 10px", borderRadius: 99, border: `1px solid ${s.color}55`, background: `${s.color}14` }}>
                <span style={{ width: 8, height: 8, borderRadius: 99, background: s.color }} />
                {t(s.name)}
                <button onClick={() => { if (confirm(t("deleteStatusWarning"))) deleteStatusMut.mutate(s.id); }} title={t("remove")} style={{ background: "transparent", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: 0, fontSize: 11 }}>x</button>
              </span>
            ))}
          </div>
        </>
      )}

      {tab === "trash" && <TrashTab />}

      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button onClick={onClose} style={btnStyle}>{t("close")}</button>
      </div>
    </div>
  );
}

function TrashTab() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const { data: trash } = useQuery({ queryKey: ["trash"], queryFn: fetchTrash });

  const restoreBoardMut = useMutation({
    mutationFn: (id: string) => restoreBoard(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["trash"] }); qc.invalidateQueries({ queryKey: ["boards"] }); qc.invalidateQueries({ queryKey: ["tasks"] }); },
  });
  const restoreTaskMut = useMutation({
    mutationFn: (id: string) => restoreTask(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["trash"] }); qc.invalidateQueries({ queryKey: ["tasks"] }); },
  });
  const purgeBoardMut = useMutation({
    mutationFn: (id: string) => purgeBoard(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trash"] }),
  });
  const purgeTaskMut = useMutation({
    mutationFn: (id: string) => purgeTask(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trash"] }),
  });
  const restoreWsMut = useMutation({
    mutationFn: (id: string) => restoreWorkspace(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["trash"] }); qc.invalidateQueries({ queryKey: ["workspaces"] }); qc.invalidateQueries({ queryKey: ["boards"] }); qc.invalidateQueries({ queryKey: ["tasks"] }); },
  });
  const purgeWsMut = useMutation({
    mutationFn: (id: string) => purgeWorkspace(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trash"] }),
  });

  const workspaces = trash?.workspaces || [];
  const boards = trash?.boards || [];
  const tasks = trash?.tasks || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ fontSize: 10, color: "var(--text-muted)" }}>{t("trashHint")}</div>

      {workspaces.length === 0 && boards.length === 0 && tasks.length === 0 && (
        <div style={{ fontSize: 11, color: "var(--text-faint)", textAlign: "center", padding: 16 }}>{t("trashEmpty")}</div>
      )}

      {workspaces.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 700, letterSpacing: 0.4 }}>{t("boardsMenu").toUpperCase()}</div>
          {workspaces.map((w) => (
            <div key={w.id} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, padding: "5px 8px", border: "1px solid var(--border)", borderRadius: 4, flexWrap: "wrap" }}>
              <span style={{ flex: 1, minWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{w.name}</span>
              <span style={{ fontSize: 9, padding: "1px 5px", borderRadius: 99, background: "#6b728022", border: "1px solid var(--border)", color: "var(--text-muted)" }}>{w.board_count}</span>
              <span style={{ fontSize: 10, color: "var(--text-faint)", whiteSpace: "nowrap" }}>{w.expires_in_days} {t("daysLeft")}</span>
              <button onClick={() => restoreWsMut.mutate(w.id)} style={{ ...btnStyle, fontSize: 10, padding: "3px 8px", color: "#22c55e", borderColor: "#22c55e55" }}>{t("restore")}</button>
              <button onClick={() => { if (confirm(t("deleteForeverWarning"))) purgeWsMut.mutate(w.id); }} style={{ ...btnStyle, fontSize: 10, padding: "3px 8px", color: "#ef4444", borderColor: "#ef444455" }}>{t("deleteForever")}</button>
            </div>
          ))}
        </div>
      )}

      {boards.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 700, letterSpacing: 0.4 }}>{t("boards").toUpperCase()}</div>
          {boards.map((b) => (
            <div key={b.id} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, padding: "5px 8px", border: "1px solid var(--border)", borderRadius: 4, flexWrap: "wrap" }}>
              <span style={{ flex: 1, minWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{b.name}</span>
              <span style={{ fontSize: 9, padding: "1px 5px", borderRadius: 99, background: "#6b728022", border: "1px solid var(--border)", color: "var(--text-muted)" }}>{b.kind}</span>
              <span style={{ fontSize: 10, color: "var(--text-faint)", whiteSpace: "nowrap" }}>{b.expires_in_days} {t("daysLeft")}</span>
              <button onClick={() => restoreBoardMut.mutate(b.id)} style={{ ...btnStyle, fontSize: 10, padding: "3px 8px", color: "#22c55e", borderColor: "#22c55e55" }}>{t("restore")}</button>
              <button onClick={() => { if (confirm(t("deleteForeverWarning"))) purgeBoardMut.mutate(b.id); }} style={{ ...btnStyle, fontSize: 10, padding: "3px 8px", color: "#ef4444", borderColor: "#ef444455" }}>{t("deleteForever")}</button>
            </div>
          ))}
        </div>
      )}

      {tasks.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 700, letterSpacing: 0.4 }}>{t("tasks").toUpperCase()}</div>
          {tasks.map((tr) => (
            <div key={tr.id} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, padding: "5px 8px", border: "1px solid var(--border)", borderRadius: 4, flexWrap: "wrap" }}>
              <span style={{ flex: 1, minWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{tr.title}</span>
              <span style={{ fontSize: 10, color: "var(--text-faint)", whiteSpace: "nowrap" }}>{tr.expires_in_days} {t("daysLeft")}</span>
              <button onClick={() => restoreTaskMut.mutate(tr.id)} style={{ ...btnStyle, fontSize: 10, padding: "3px 8px", color: "#22c55e", borderColor: "#22c55e55" }}>{t("restore")}</button>
              <button onClick={() => { if (confirm(t("deleteForeverWarning"))) purgeTaskMut.mutate(tr.id); }} style={{ ...btnStyle, fontSize: 10, padding: "3px 8px", color: "#ef4444", borderColor: "#ef444455" }}>{t("deleteForever")}</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Inline editor for a member: name, email, phone, and a separate password field. */
function UserEditor({
  initial,
  onSave,
  onCancel,
  onPassword,
}: {
  initial: { name: string; email: string; phone: string };
  onSave: (patch: { name?: string; email?: string; phone?: string | null }) => void;
  onCancel: () => void;
  onPassword: (password: string) => void;
}) {
  const { t } = useI18n();
  const [name, setName] = useState(initial.name);
  const [email, setEmail] = useState(initial.email);
  const [phone, setPhone] = useState(initial.phone);
  const [pwd, setPwd] = useState("");
  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", padding: "6px 0 0", borderTop: "1px dashed var(--border)" }}>
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder={t("name")} style={{ ...inputStyle, flex: 1, minWidth: 110 }} />
      <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t("email")} style={{ ...inputStyle, flex: 1.2, minWidth: 150 }} />
      <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder={t("phone")} style={{ ...inputStyle, flex: 1, minWidth: 110 }} />
      <input type="password" value={pwd} onChange={(e) => setPwd(e.target.value)} placeholder={t("newPassword")} style={{ ...inputStyle, flex: 1, minWidth: 110 }} />
      <button
        onClick={() => {
          onSave({ name, email, phone: phone || null });
          if (pwd) onPassword(pwd);
        }}
        disabled={!name.trim() || !email.trim()}
        style={{ ...btnStyle, background: "#3b82f6", color: "#fff", borderColor: "#3b82f6", opacity: name.trim() && email.trim() ? 1 : 0.5 }}
      >
        {t("save")}
      </button>
      <button onClick={onCancel} style={btnStyle}>{t("cancel")}</button>
    </div>
  );
}

/** Controlled select that resets to placeholder after adding. */
function MemberSelect({
  teamId,
  candidates,
  onAdd,
  label,
}: {
  teamId: string;
  candidates: { id: string; name: string; email: string }[];
  onAdd: (userId: string) => void;
  label: string;
}) {
  const [value, setValue] = useState("");
  return (
    <select
      value={value}
      onChange={(e) => {
        const v = e.target.value;
        if (!v) return;
        setValue("");
        onAdd(v);
      }}
      style={{ ...inputStyle, width: "100%" }}
    >
      <option value="">{label}...</option>
      {candidates.map((u) => (
        <option key={`${teamId}-${u.id}`} value={u.id}>{u.name || u.email}</option>
      ))}
    </select>
  );
}
