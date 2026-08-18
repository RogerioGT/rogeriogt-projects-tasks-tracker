import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchStatuses, fetchBoards, updateTask, deleteTask, Task } from "../api";
import { useI18n } from "../i18n";
import ShareDialog from "./ShareDialog";

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
  padding: "5px 10px",
  border: "1px solid var(--border)",
  borderRadius: 4,
  background: "var(--bg-elevated)",
  color: "var(--text)",
  cursor: "pointer",
};

export default function TaskEditDialog({
  task,
  onClose,
}: {
  task: Task;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [title, setTitle] = useState(task.title);
  const [desc, setDesc] = useState(task.description || "");
  const [status, setStatus] = useState<string>(task.status);
  const [priority, setPriority] = useState<string>(task.priority);
  const [assignee, setAssignee] = useState(task.assignee || "");
  const [due, setDue] = useState(task.due_date || "");
  const [tags, setTags] = useState((task.tags || []).join(", "));
  const [shareOpen, setShareOpen] = useState(false);
  const [error, setError] = useState("");

  const { data: statuses } = useQuery({ queryKey: ["statuses"], queryFn: fetchStatuses });
  const { data: boards } = useQuery({ queryKey: ["boards", "flat"], queryFn: fetchBoards });
  const boardName = new Map((boards || []).map((b) => [b.id, b.name]));

  const updateMut = useMutation({
    mutationFn: () =>
      updateTask(task.id, {
        title,
        description: desc || null,
        status,
        priority: priority as Task["priority"],
        assignee: assignee || null,
        due_date: due || null,
        tags: tags ? tags.split(",").map((s) => s.trim()).filter(Boolean) : null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      onClose();
    },
    onError: (e) => setError(e instanceof Error ? e.message : String(e)),
  });

  const deleteMut = useMutation({
    mutationFn: () => deleteTask(task.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      onClose();
    },
  });

  // status names: union of defined statuses + the task's own status
  const statusNames = new Set<string>((statuses || []).map((s) => s.name));
  statusNames.add(task.status);
  const statusOptions = Array.from(statusNames);

  return (
    <div onClick={(e) => e.stopPropagation()} style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8, padding: 16, minWidth: 380, maxWidth: 460, display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ fontSize: 12, fontWeight: 700, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t("editTask")}</span>
        <span style={{ fontSize: 9, color: "var(--text-faint)", fontWeight: 400 }}>{boardName.get(task.board_id) || ""}</span>
      </div>

      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t("title")} style={inputStyle} autoFocus />
      <textarea value={desc} onChange={(e) => setDesc(e.target.value)} placeholder={t("description")} rows={3} style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit" }} />

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <select value={status} onChange={(e) => setStatus(e.target.value)} style={{ ...inputStyle, flex: 1 }}>
          {statusOptions.map((s) => (
            <option key={s} value={s}>{t(s)}</option>
          ))}
        </select>
        <select value={priority} onChange={(e) => setPriority(e.target.value)} style={{ ...inputStyle, flex: 1 }}>
          <option value="high">{t("high")}</option>
          <option value="medium">{t("medium")}</option>
          <option value="low">{t("low")}</option>
          <option value="none">{t("none")}</option>
        </select>
      </div>

      <div style={{ display: "flex", gap: 6 }}>
        <input value={assignee} onChange={(e) => setAssignee(e.target.value)} placeholder={t("assignee")} style={{ ...inputStyle, flex: 1 }} />
        <input type="date" value={due} onChange={(e) => setDue(e.target.value)} style={{ ...inputStyle, width: 140 }} />
      </div>

      <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder={t("tags") + " (comma separated)"} style={inputStyle} />

      {error && <div style={{ fontSize: 10, color: "#ef4444" }}>{error}</div>}

      <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
        <button onClick={() => setShareOpen(true)} style={btnStyle}>{t("share")}</button>
        <button onClick={() => { if (confirm(t("confirmDelete"))) deleteMut.mutate(); }} style={{ ...btnStyle, color: "#ef4444", borderColor: "#ef444455" }}>{t("delete")}</button>
        <button onClick={onClose} style={btnStyle}>{t("cancel")}</button>
        <button onClick={() => updateMut.mutate()} disabled={!title.trim()} style={{ ...btnStyle, background: "#3b82f6", color: "#fff", borderColor: "#3b82f6", opacity: title.trim() ? 1 : 0.5 }}>{t("save")}</button>
      </div>

      {shareOpen && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 70 }} onClick={() => setShareOpen(false)}>
          <ShareDialog scope={{ type: "task", taskIds: [task.id], label: "" }} onClose={() => setShareOpen(false)} />
        </div>
      )}
    </div>
  );
}
