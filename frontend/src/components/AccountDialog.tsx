import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { changePassword, createWorkspace, deleteWorkspace, renameWorkspace, updateMe } from "../api";
import { useAuth } from "../auth";
import { useWorkspace } from "../workspace";
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
  padding: "5px 10px",
  border: "1px solid var(--border)",
  borderRadius: 4,
  background: "var(--bg-elevated)",
  color: "var(--text)",
  cursor: "pointer",
};

export default function AccountDialog({ onClose }: { onClose: () => void }) {
  const { t } = useI18n();
  const { user, required, login, register, logout } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const [curPass, setCurPass] = useState("");
  const [newPass, setNewPass] = useState("");
  const [pwMsg, setPwMsg] = useState("");

  // own profile
  const { refreshUser } = useAuth();
  const [pName, setPName] = useState(user ? user.name : "");
  const [pEmail, setPEmail] = useState(user ? user.email : "");
  const [pPhone, setPPhone] = useState(user?.phone || "");
  const [pMsg, setPMsg] = useState("");
  const profileMut = useMutation({
    mutationFn: () => updateMe({ name: pName, email: pEmail, phone: pPhone || null }),
    onSuccess: (u) => { refreshUser(u); setPMsg(t("saved")); setTimeout(() => setPMsg(""), 3000); },
    onError: (e) => setPMsg(e instanceof Error ? e.message : String(e)),
  });

  // workspaces (main boards)
  const qc = useQueryClient();
  const { workspaces, currentId, setCurrentId, refresh } = useWorkspace();
  const [newBoardName, setNewBoardName] = useState("");
  const [renameId, setRenameId] = useState<string | null>(null);
  const [renameVal, setRenameVal] = useState("");
  const [wsMsg, setWsMsg] = useState("");
  const createMut = useMutation({
    mutationFn: () => createWorkspace(newBoardName),
    onSuccess: (ws) => { qc.invalidateQueries({ queryKey: ["workspaces"] }); setCurrentId(ws.id); setNewBoardName(""); refresh(); },
    onError: (e) => setWsMsg(e instanceof Error ? e.message : String(e)),
  });
  const renameMut = useMutation({
    mutationFn: ({ id, name }: { id: string; name: string }) => renameWorkspace(id, name),
    onSuccess: () => { setRenameId(null); refresh(); },
    onError: (e) => setWsMsg(e instanceof Error ? e.message : String(e)),
  });
  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteWorkspace(id),
    onSuccess: (_d, id) => { if (currentId === id) { const next = workspaces.find((w) => w.id !== id); if (next) setCurrentId(next.id); } refresh(); },
    onError: (e) => setWsMsg(e instanceof Error ? e.message : String(e)),
  });

  const submit = async () => {
    setError("");
    try {
      if (mode === "login") await login(email, password);
      else await register(email, name, password);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const doChangePassword = async () => {
    setPwMsg("");
    try {
      await changePassword(curPass, newPass);
      setPwMsg(t("saved"));
      setCurPass("");
      setNewPass("");
    } catch (e) {
      setPwMsg(e instanceof Error ? e.message : String(e));
    }
  };

  if (user) {
    return (
      <div onClick={(e) => e.stopPropagation()} style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8, padding: 16, minWidth: 300, display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ fontSize: 12, fontWeight: 700 }}>{t("account")}</div>
        <div style={{ fontSize: 11 }}>
          <div style={{ color: "var(--text)" }}>{user.name || user.email}</div>
          <div style={{ color: "var(--text-muted)" }}>{user.email}</div>
          {user.is_admin && <div style={{ fontSize: 9, color: "#a78bfa", marginTop: 2 }}>{t("admin")}</div>}
        </div>

        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ fontSize: 11, fontWeight: 600 }}>{t("profile")}</div>
          <input value={pName} onChange={(e) => setPName(e.target.value)} placeholder={t("name")} style={inputStyle} />
          <input value={pEmail} onChange={(e) => setPEmail(e.target.value)} placeholder={t("email")} style={inputStyle} />
          <input value={pPhone} onChange={(e) => setPPhone(e.target.value)} placeholder={t("phone")} style={inputStyle} />
          {pMsg && <div style={{ fontSize: 10, color: pMsg === t("saved") ? "#22c55e" : "#ef4444" }}>{pMsg}</div>}
          <button onClick={() => profileMut.mutate()} disabled={!pName.trim() || !pEmail.trim()} style={{ ...btnStyle, opacity: pName.trim() && pEmail.trim() ? 1 : 0.5 }}>{t("save")}</button>
        </div>

        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ fontSize: 11, fontWeight: 600 }}>{t("boardsMenu")}</div>
          {workspaces.map((w) => (
            <div key={w.id} style={{ display: "flex", alignItems: "center", gap: 4 }}>
              {renameId === w.id ? (
                <>
                  <input value={renameVal} onChange={(e) => setRenameVal(e.target.value)} style={{ ...inputStyle, flex: 1 }} autoFocus
                    onKeyDown={(e) => { if (e.key === "Enter") renameMut.mutate({ id: w.id, name: renameVal }); if (e.key === "Escape") setRenameId(null); }} />
                  <button onClick={() => renameMut.mutate({ id: w.id, name: renameVal })} style={btnStyle}>{t("save")}</button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => { setCurrentId(w.id); }}
                    style={{
                      ...btnStyle, flex: 1, textAlign: "left", display: "flex", justifyContent: "space-between", gap: 8,
                      background: w.id === currentId ? "var(--bg)" : "transparent",
                      fontWeight: w.id === currentId ? 700 : 400,
                    }}
                  >
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{w.name}</span>
                    <span style={{ fontSize: 9, color: "var(--text-faint)", fontWeight: 400 }}>{w.board_count}</span>
                  </button>
                  <button title={t("rename")} onClick={() => { setRenameId(w.id); setRenameVal(w.name); setWsMsg(""); }} style={{ ...btnStyle, padding: "4px 6px" }}>✎</button>
                  <button title={t("delete")} onClick={() => { if (confirm(t("deleteWorkspaceWarning"))) deleteMut.mutate(w.id); }} style={{ ...btnStyle, padding: "4px 6px", color: "#ef4444", borderColor: "#ef444455" }}>🗑</button>
                </>
              )}
            </div>
          ))}
          <div style={{ display: "flex", gap: 4 }}>
            <input
              value={newBoardName}
              onChange={(e) => setNewBoardName(e.target.value)}
              placeholder={t("newBoardPlaceholder")}
              style={{ ...inputStyle, flex: 1 }}
              onKeyDown={(e) => { if (e.key === "Enter" && newBoardName.trim()) createMut.mutate(); }}
            />
            <button onClick={() => { if (newBoardName.trim()) createMut.mutate(); }} disabled={!newBoardName.trim()} style={{ ...btnStyle, background: "#3b82f6", color: "#fff", borderColor: "#3b82f6", opacity: newBoardName.trim() ? 1 : 0.5 }}>+ {t("newBoard")}</button>
          </div>
          {wsMsg && <div style={{ fontSize: 10, color: "#ef4444" }}>{wsMsg}</div>}
        </div>

        <div style={{ borderTop: "1px solid var(--border)", paddingTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ fontSize: 11, fontWeight: 600 }}>{t("changePassword")}</div>
          <input type="password" value={curPass} onChange={(e) => setCurPass(e.target.value)} placeholder={t("currentPassword")} style={inputStyle} />
          <input type="password" value={newPass} onChange={(e) => setNewPass(e.target.value)} placeholder={t("newPassword")} style={inputStyle} />
          {pwMsg && <div style={{ fontSize: 10, color: pwMsg === t("saved") ? "#22c55e" : "#ef4444" }}>{pwMsg}</div>}
          <button onClick={doChangePassword} disabled={!curPass || !newPass} style={{ ...btnStyle, opacity: curPass && newPass ? 1 : 0.5 }}>{t("changePassword")}</button>
        </div>

        <button onClick={() => { logout(); onClose(); }} style={{ ...btnStyle, color: "#ef4444", borderColor: "#ef444455" }}>{t("logout")}</button>
      </div>
    );
  }

  return (
    <div onClick={(e) => e.stopPropagation()} style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8, padding: 16, minWidth: 300, display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ fontSize: 12, fontWeight: 700 }}>{mode === "login" ? t("login") : t("register")}</div>
      {mode === "register" && <input value={name} onChange={(e) => setName(e.target.value)} placeholder={t("name")} style={inputStyle} />}
      <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t("email")} style={inputStyle} autoFocus />
      <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder={t("password")} style={inputStyle} onKeyDown={(e) => { if (e.key === "Enter") submit(); }} />
      {error && <div style={{ fontSize: 10, color: "#ef4444" }}>{error}</div>}
      <button onClick={submit} style={{ ...btnStyle, background: "#3b82f6", color: "#fff", borderColor: "#3b82f6" }}>{mode === "login" ? t("login") : t("register")}</button>
      {!required && (
        <button onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }} style={{ ...btnStyle, background: "transparent" }}>
          {mode === "login" ? t("noAccount") : t("haveAccount")}
        </button>
      )}
    </div>
  );
}
