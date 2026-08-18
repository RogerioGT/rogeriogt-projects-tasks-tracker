import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createWorkspace, Workspace } from "../api";
import { useWorkspace } from "../workspace";
import { useI18n } from "../i18n";

const btnStyle: React.CSSProperties = {
  fontSize: 11,
  padding: "4px 10px",
  border: "1px solid var(--border)",
  borderRadius: 4,
  background: "var(--bg-elevated)",
  color: "var(--text)",
  cursor: "pointer",
};

export default function WorkspaceSwitcher() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const { workspaces, current, currentId, setCurrentId, refresh } = useWorkspace();
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const wrapRef = useRef<HTMLDivElement>(null);

  const createMut = useMutation({
    mutationFn: () => createWorkspace(name),
    onSuccess: (ws: Workspace) => {
      qc.invalidateQueries({ queryKey: ["workspaces"] });
      setCurrentId(ws.id);
      setCreating(false);
      setName("");
      setOpen(false);
    },
    onError: (e) => setError(e instanceof Error ? e.message : String(e)),
  });

  return (
    <div ref={wrapRef} style={{ position: "relative" }}>
      <button
        onClick={() => { setOpen(!open); setError(""); }}
        title={t("boardsMenu")}
        style={{
          ...btnStyle,
          display: "flex",
          alignItems: "center",
          gap: 6,
          maxWidth: 220,
          overflow: "hidden",
        }}
      >
        <span style={{ fontSize: 9, opacity: 0.7 }}>▦</span>
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {current ? current.name : t("boardsMenu")}
        </span>
        <span style={{ fontSize: 9, opacity: 0.6 }}>▼</span>
      </button>
      {open && (
        <div
          style={{
            position: "fixed",
            top: (wrapRef.current?.getBoundingClientRect().bottom ?? 40) + 4,
            right: Math.max(8, window.innerWidth - (wrapRef.current?.getBoundingClientRect().right ?? 0)),
            zIndex: 65,
            background: "var(--bg-elevated)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            padding: 6,
            minWidth: 220,
            maxHeight: "60vh",
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: 3,
            boxShadow: "0 8px 24px rgba(0,0,0,0.35)",
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div style={{ fontSize: 10, fontWeight: 700, color: "var(--text-muted)", padding: "2px 8px" }}>
            {t("boardsMenu")}
          </div>
          {workspaces.map((w) => (
            <button
              key={w.id}
              onClick={() => { setCurrentId(w.id); setOpen(false); }}
              style={{
                ...btnStyle,
                border: "none",
                textAlign: "left",
                display: "flex",
                justifyContent: "space-between",
                gap: 8,
                background: w.id === currentId ? "var(--bg)" : "transparent",
                fontWeight: w.id === currentId ? 700 : 400,
              }}
            >
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{w.name}</span>
              <span style={{ fontSize: 9, color: "var(--text-faint)" }}>{w.board_count}</span>
            </button>
          ))}
          {creating ? (
            <div style={{ display: "flex", gap: 4, padding: "2px 8px 2px" }}>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t("newBoardPlaceholder")}
                style={{
                  fontSize: 11,
                  padding: "4px 8px",
                  border: "1px solid var(--border)",
                  borderRadius: 4,
                  background: "var(--bg)",
                  color: "var(--text)",
                  flex: 1,
                  minWidth: 0,
                }}
                autoFocus
                onKeyDown={(e) => { if (e.key === "Enter" && name.trim()) createMut.mutate(); if (e.key === "Escape") { setCreating(false); setName(""); } }}
              />
              <button
                onClick={() => { if (name.trim()) createMut.mutate(); }}
                disabled={!name.trim()}
                style={{ ...btnStyle, background: "#3b82f6", color: "#fff", borderColor: "#3b82f6", opacity: name.trim() ? 1 : 0.5 }}
              >
                {t("save")}
              </button>
            </div>
          ) : (
            <button
              onClick={() => { setCreating(true); setError(""); refresh(); }}
              style={{ ...btnStyle, border: "1px dashed var(--border-strong)", textAlign: "left", color: "var(--text-muted)" }}
            >
              + {t("newBoard")}
            </button>
          )}
          {error && <div style={{ fontSize: 10, color: "#ef4444", padding: "0 8px" }}>{error}</div>}
        </div>
      )}
    </div>
  );
}
