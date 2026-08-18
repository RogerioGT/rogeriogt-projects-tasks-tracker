import { useState } from "react";
import { changePassword } from "../api";
import { useAuth } from "../auth";
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
