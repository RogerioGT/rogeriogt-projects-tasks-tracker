import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useVirtualizer } from "@tanstack/react-virtual";
import { fetchBoardTree, fetchTasks, fetchStatuses, createTask, toggleComplete, updateTask, createBoard, updateBoard, deleteBoard, deleteTask, convertTaskToProject, Task, fetchBoards, BoardTreeNode } from "../api";
import { useI18n } from "../i18n";
import ShareDialog from "../components/ShareDialog";

const priorityColor: Record<string, string> = {
  high: "#ef4444",
  medium: "#f97316",
  low: "#3b82f6",
  none: "#6b7280",
};

const statusColor: Record<string, string> = {
  not_started: "#6b7280",
  in_progress: "#3b82f6",
  waiting: "#eab308",
  done: "#22c55e",
};

function TaskRow({
  task,
  onToggle,
  onUpdate,
  onDelete,
  onShare,
  onConvert,
}: {
  task: Task;
  onToggle: () => void;
  onUpdate: (patch: Partial<Task>) => void;
  onDelete: () => void;
  onShare: () => void;
  onConvert: () => void;
}) {
  const { t } = useI18n();
  const { data: statuses } = useQuery({ queryKey: ["statuses"], queryFn: fetchStatuses });
  const [open, setOpen] = useState(false);
  const [editTitle, setEditTitle] = useState(task.title);
  const [editDesc, setEditDesc] = useState(task.description || "");
  const [editStatus, setEditStatus] = useState<string>(task.status);
  const [editPriority, setEditPriority] = useState<string>(task.priority);
  const [editAssignee, setEditAssignee] = useState(task.assignee || "");
  const [editDue, setEditDue] = useState(task.due_date || "");
  const [editTags, setEditTags] = useState((task.tags || []).join(", "));

  // status options: defined + the task's own
  const statusOptions = new Set<string>((statuses || []).map((s) => s.name));
  statusOptions.add(task.status);

  const save = () => {
    onUpdate({
      title: editTitle,
      description: editDesc || null,
      status: editStatus as Task["status"],
      priority: editPriority as Task["priority"],
      assignee: editAssignee || null,
      due_date: editDue || null,
      tags: editTags ? editTags.split(",").map((s) => s.trim()).filter(Boolean) : null,
    } as Partial<Task>);
    setOpen(false);
  };

  return (
    <div
      style={{
        border: "1px solid var(--border)",
        borderRadius: 4,
        padding: "4px 6px",
        background: "var(--bg-surface)",
        display: "flex",
        flexDirection: "column",
        gap: 2,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6, minHeight: "var(--row-h)" }}>
        <input type="checkbox" checked={task.status === "done"} onChange={onToggle} style={{ accentColor: "#22c55e", width: 12, height: 12 }} />
        <button
          onClick={() => setOpen(!open)}
          style={{
            flex: 1,
            textAlign: "left",
            fontSize: 11,
            color: task.status === "done" ? "var(--text-faint)" : "var(--text)",
            textDecoration: task.status === "done" ? "line-through" : "none",
            background: "transparent",
            border: "none",
            cursor: "pointer",
            padding: 0,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
          title={task.title}
        >
          {task.title}
        </button>
        <span
          style={{
            fontSize: 9,
            padding: "1px 4px",
            borderRadius: 3,
            background: priorityColor[task.priority] + "22",
            color: priorityColor[task.priority],
            border: `1px solid ${priorityColor[task.priority]}55`,
            whiteSpace: "nowrap",
          }}
        >
          {t(task.priority)}
        </span>
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: 99,
            background: statusColor[task.status],
            flexShrink: 0,
          }}
          title={t(task.status)}
        />
      </div>

      {task.assignee || task.due_date ? (
        <div style={{ display: "flex", gap: 6, fontSize: 10, color: "var(--text-faint)", paddingLeft: 20 }}>
          {task.assignee && <span>{task.assignee}</span>}
          {task.due_date && <span>{task.due_date}</span>}
        </div>
      ) : null}

      {open && (
        <div style={{ borderTop: "1px solid var(--border)", marginTop: 4, paddingTop: 6, display: "flex", flexDirection: "column", gap: 6 }}>
          <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} placeholder={t("title")} style={inputStyle} />
          <textarea value={editDesc} onChange={(e) => setEditDesc(e.target.value)} placeholder={t("description")} rows={2} style={{ ...inputStyle, resize: "vertical" }} />
          <div style={{ display: "flex", gap: 6 }}>
            <select value={editStatus} onChange={(e) => setEditStatus(e.target.value)} style={inputStyle}>
              {Array.from(statusOptions).map((s) => (
                <option key={s} value={s}>{t(s)}</option>
              ))}
            </select>
            <select value={editPriority} onChange={(e) => setEditPriority(e.target.value as Task["priority"])} style={inputStyle}>
              <option value="high">{t("high")}</option>
              <option value="medium">{t("medium")}</option>
              <option value="low">{t("low")}</option>
              <option value="none">{t("none")}</option>
            </select>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <input value={editAssignee} onChange={(e) => setEditAssignee(e.target.value)} placeholder={t("assignee")} style={inputStyle} />
            <input type="date" value={editDue} onChange={(e) => setEditDue(e.target.value)} style={inputStyle} />
          </div>
          <input value={editTags} onChange={(e) => setEditTags(e.target.value)} placeholder={t("tags") + " (comma separated)"} style={inputStyle} />
          <div style={{ display: "flex", gap: 6, justifyContent: "flex-end", flexWrap: "wrap" }}>
            <button onClick={onShare} style={{ ...btnStyle }}>{t("share")}</button>
            <button onClick={onConvert} style={{ ...btnStyle }}>{t("convertToProject")}</button>
            <button onClick={onDelete} style={{ ...btnStyle, color: "#ef4444", borderColor: "#ef444455" }}>{t("delete")}</button>
            <button onClick={() => setOpen(false)} style={btnStyle}>{t("cancel")}</button>
            <button onClick={save} style={{ ...btnStyle, background: "#3b82f6", color: "#fff", borderColor: "#3b82f6" }}>{t("save")}</button>
          </div>
        </div>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  fontSize: 11,
  padding: "4px 6px",
  border: "1px solid var(--border)",
  borderRadius: 4,
  background: "var(--bg)",
  color: "var(--text)",
  width: "100%",
  boxSizing: "border-box",
};

const btnStyle: React.CSSProperties = {
  fontSize: 11,
  padding: "3px 8px",
  border: "1px solid var(--border)",
  borderRadius: 4,
  background: "var(--bg-elevated)",
  color: "var(--text)",
  cursor: "pointer",
};

function Column({
  board,
  tasksAll,
  depth,
  onAddBoard,
}: {
  board: BoardTreeNode;
  tasksAll: Task[];
  depth: number;
  onAddBoard: (parentId: string) => void;
}) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [newTitle, setNewTitle] = useState("");
  const [showCompleted, setShowCompleted] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [taskShareId, setTaskShareId] = useState<string>("");
  const [editName, setEditName] = useState(board.name);
  const [editColor, setEditColor] = useState(board.color);

  const active = tasksAll.filter((x) => x.board_id === board.id && x.status !== "done");
  const done = tasksAll.filter((x) => x.board_id === board.id && x.status === "done");

  const createMut = useMutation({
    mutationFn: (title: string) => createTask({ board_id: board.id, title }),
    onSettled: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });
  const toggleMut = useMutation({
    mutationFn: (id: string) => toggleComplete(id),
    onSettled: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });
  const convertMut = useMutation({
    mutationFn: (id: string) => convertTaskToProject(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["tasks"] });
      qc.invalidateQueries({ queryKey: ["boards"] });
    },
  });
  const updateMut = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Partial<Task> }) => updateTask(id, patch as never),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });
  const deleteTaskMut = useMutation({
    mutationFn: (id: string) => deleteTask(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const updateBoardMut = useMutation({
    mutationFn: () => updateBoard(board.id, { name: editName, color: editColor }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["boards"] }); setMenuOpen(false); },
  });
  const deleteBoardMut = useMutation({
    mutationFn: () => deleteBoard(board.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["boards"] }),
  });

  const parentRef = useRef<HTMLDivElement>(null);
  const rowVirtualizer = useVirtualizer({
    count: active.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 34,
    overscan: 8,
  });

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    createMut.mutate(newTitle.trim());
    setNewTitle("");
  };

  const isNestedParent = board.children.length > 0;

  return (
    <div
      style={{
        width: 240,
        minWidth: 240,
        display: "flex",
        flexDirection: "column",
        border: "1px solid var(--border)",
        borderRadius: 6,
        background: "var(--bg-surface)",
        overflow: "hidden",
        maxHeight: "calc(100vh - 84px)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          padding: "6px 8px",
          borderBottom: "1px solid var(--border)",
          background: depth === 0 ? "var(--bg-elevated)" : "var(--bg-surface)",
          position: "relative",
        }}
      >
        <span style={{ width: 3, alignSelf: "stretch", background: board.color, borderRadius: 2, marginRight: 2 }} />
        <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{board.name}</span>
        <span style={{ fontSize: 10, color: "var(--text-faint)", background: "var(--bg)", padding: "1px 5px", borderRadius: 99, border: "1px solid var(--border)" }}>
          {active.length + done.length}
        </span>
        <button onClick={() => setMenuOpen(!menuOpen)} style={{ fontSize: 12, padding: "2px 6px", border: "1px solid var(--border)", borderRadius: 4, background: "var(--bg)", color: "var(--text-muted)", cursor: "pointer" }}>
          ...
        </button>
        {menuOpen && (
          <div style={{ position: "absolute", top: "100%", right: 4, marginTop: 4, background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 6, padding: 8, minWidth: 180, zIndex: 10, display: "flex", flexDirection: "column", gap: 6 }}>
            <input value={editName} onChange={(e) => setEditName(e.target.value)} style={inputStyle} placeholder={t("title")} />
            <input type="color" value={editColor} onChange={(e) => setEditColor(e.target.value)} style={{ width: "100%", height: 28, border: "1px solid var(--border)", borderRadius: 4, background: "var(--bg)" }} />
            <div style={{ display: "flex", gap: 6 }}>
              <button onClick={() => updateBoardMut.mutate()} style={{ ...btnStyle, flex: 1, background: "#3b82f6", color: "#fff", borderColor: "#3b82f6" }}>{t("save")}</button>
              <button onClick={() => setMenuOpen(false)} style={{ ...btnStyle, flex: 1 }}>{t("cancel")}</button>
            </div>
            <button onClick={() => onAddBoard(board.id)} style={{ ...btnStyle, textAlign: "left" }}>{t("addProject")}</button>
            <button onClick={() => { setMenuOpen(false); setShareOpen(true); }} style={{ ...btnStyle, textAlign: "left" }}>{t("share")}</button>
            <button onClick={() => { if (confirm("Delete board and its tasks?")) deleteBoardMut.mutate(); }} style={{ ...btnStyle, color: "#ef4444", borderColor: "#ef444455" }}>{t("delete")}</button>
          </div>
        )}
      </div>

      <form onSubmit={handleAdd} style={{ padding: "6px 6px 4px", borderBottom: "1px solid var(--border)", display: "flex", gap: 4, background: "var(--bg-surface)", position: "sticky", top: 0 }}>
        <input value={newTitle} onChange={(e) => setNewTitle(e.target.value)} placeholder={t("newTaskPlaceholder")} style={{ ...inputStyle, flex: 1 }} />
        <button type="submit" style={{ ...btnStyle, background: board.color, color: "#fff", borderColor: board.color, whiteSpace: "nowrap" }}>{t("addTask")}</button>
      </form>

      {isNestedParent ? (
        <div style={{ flex: 1, overflow: "auto", padding: 6, display: "flex", flexDirection: "column", gap: 8 }}>
          {board.children.map((child) => (
            <Column key={child.id} board={child} tasksAll={tasksAll} depth={depth + 1} onAddBoard={onAddBoard} />
          ))}
          {board.children.length === 0 && <div style={{ fontSize: 11, color: "var(--text-faint)", textAlign: "center", padding: 8 }}>{t("noTasks")}</div>}
        </div>
      ) : (
        <>
          <div ref={parentRef} style={{ flex: 1, overflow: "auto", padding: 6, display: "flex", flexDirection: "column", gap: 4 }}>
            {active.length === 0 ? (
              <div style={{ fontSize: 11, color: "var(--text-faint)", textAlign: "center", padding: 12 }}>{t("noTasks")}</div>
            ) : active.length > 12 ? (
              <div style={{ height: rowVirtualizer.getTotalSize(), position: "relative" }}>
                {rowVirtualizer.getVirtualItems().map((vi) => {
                  const task = active[vi.index];
                  return (
                    <div key={task.id} style={{ position: "absolute", top: 0, left: 0, width: "100%", transform: `translateY(${vi.start}px)`, paddingBottom: 4 }}>
                      <TaskRow task={task} onToggle={() => toggleMut.mutate(task.id)} onUpdate={(patch) => updateMut.mutate({ id: task.id, patch })} onDelete={() => deleteTaskMut.mutate(task.id)} onShare={() => setTaskShareId(task.id)} onConvert={() => { if (confirm(t("convertConfirm"))) convertMut.mutate(task.id); }} />
                    </div>
                  );
                })}
              </div>
            ) : (
              active.map((task) => (
                <TaskRow key={task.id} task={task} onToggle={() => toggleMut.mutate(task.id)} onUpdate={(patch) => updateMut.mutate({ id: task.id, patch })} onDelete={() => deleteTaskMut.mutate(task.id)} onShare={() => setTaskShareId(task.id)} onConvert={() => { if (confirm(t("convertConfirm"))) convertMut.mutate(task.id); }} />
              ))
            )}
          </div>

          {done.length > 0 && (
            <div style={{ borderTop: "1px solid var(--border)", background: "var(--bg)", padding: "4px 6px" }}>
              <button onClick={() => setShowCompleted(!showCompleted)} style={{ fontSize: 10, color: "var(--text-muted)", background: "transparent", border: "none", cursor: "pointer", width: "100%", textAlign: "left", padding: "2px 0" }}>
                {showCompleted ? "▾" : "▸"} {t("completed")} ({done.length})
              </button>
              {showCompleted && <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 4, opacity: 0.75 }}>{done.map((task) => (<TaskRow key={task.id} task={task} onToggle={() => toggleMut.mutate(task.id)} onUpdate={(patch) => updateMut.mutate({ id: task.id, patch })} onDelete={() => deleteTaskMut.mutate(task.id)} onShare={() => setTaskShareId(task.id)} onConvert={() => { if (confirm(t("convertConfirm"))) convertMut.mutate(task.id); }} />))}</div>}
            </div>
          )}
        </>
      )}

      {shareOpen && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }} onClick={() => setShareOpen(false)}>
          <ShareDialog scope={{ type: "board", boardId: board.id, boardName: board.name }} onClose={() => setShareOpen(false)} />
        </div>
      )}

      {taskShareId && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }} onClick={() => setTaskShareId("")}>
          <ShareDialog scope={{ type: "task", taskIds: [taskShareId], label: "" }} onClose={() => setTaskShareId("")} />
        </div>
      )}
    </div>
  );
}

export default function BoardView({ search }: { search: string }) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const { data: tree } = useQuery({ queryKey: ["boards", "tree"], queryFn: fetchBoardTree });
  const { data: tasks } = useQuery({ queryKey: ["tasks", { search }], queryFn: () => fetchTasks({ search: search || undefined, sort: "position" }) });
  const { data: flatBoards } = useQuery({ queryKey: ["boards", "flat"], queryFn: fetchBoards });

  const [addParent, setAddParent] = useState<string | null>(null);
  const [newBoardName, setNewBoardName] = useState("");

  const createBoardMut = useMutation({
    mutationFn: () => createBoard({ name: newBoardName, parent_id: addParent, kind: addParent ? "project" : "section", sort_order: 0 }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["boards"] }); setAddParent(null); setNewBoardName(""); },
  });

  const addTopSection = () => {
    const name = prompt(t("addSection"));
    if (name?.trim()) createBoard({ name: name.trim(), kind: "section", sort_order: 0 }).then(() => qc.invalidateQueries({ queryKey: ["boards"] }));
  };

  if (!tree || !tasks) return <div style={{ padding: 16, fontSize: 11, color: "var(--text-muted)" }}>Loading...</div>;

  const boardMap = new Map((flatBoards || []).map((b) => [b.id, b]));

  return (
    <div style={{ padding: 8, display: "flex", flexDirection: "column", gap: 10 }}>
      {(tree as BoardTreeNode[]).map((section) => (
        <div key={section.id} style={{ border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden", background: "var(--bg-surface)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 10px", background: section.color, color: "#fff" }}>
            <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: 0.2 }}>{section.name}</span>
            <span style={{ fontSize: 10, background: "rgba(255,255,255,0.2)", padding: "1px 6px", borderRadius: 99 }}>{section.children.length} columns</span>
            <div style={{ flex: 1 }} />
            <button onClick={() => setAddParent(section.id)} style={{ fontSize: 11, padding: "2px 8px", borderRadius: 4, border: "1px solid rgba(255,255,255,0.5)", background: "rgba(255,255,255,0.15)", color: "#fff", cursor: "pointer" }}>
              + {t("addColumn")}
            </button>
          </div>

          <div style={{ display: "flex", gap: 6, padding: 6, overflowX: "auto", alignItems: "flex-start", minHeight: 120 }}>
            {section.children.length === 0 ? (
              <div style={{ fontSize: 11, color: "var(--text-faint)", padding: 12 }}>{t("noTasks")} — {t("addColumn")}</div>
            ) : (
              section.children.map((col) => <Column key={col.id} board={col} tasksAll={tasks as Task[]} depth={0} onAddBoard={setAddParent} />)
            )}
          </div>
        </div>
      ))}

      <div style={{ display: "flex", gap: 8, padding: "4px 2px" }}>
        <button onClick={addTopSection} style={{ fontSize: 11, padding: "4px 10px", border: "1px dashed var(--border-strong)", borderRadius: 6, background: "transparent", color: "var(--text-muted)", cursor: "pointer" }}>
          + {t("addSection")}
        </button>
        <span style={{ fontSize: 10, color: "var(--text-faint)", alignSelf: "center" }}>{(flatBoards || []).length} boards · {(tasks as Task[]).length} tasks</span>
      </div>

      {addParent !== null && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }} onClick={() => setAddParent(null)}>
          <div onClick={(e) => e.stopPropagation()} style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8, padding: 16, minWidth: 320, display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 700 }}>
              {addParent ? `${t("addProject")} — ${boardMap.get(addParent)?.name || ""}` : t("addSection")}
            </div>
            <input value={newBoardName} onChange={(e) => setNewBoardName(e.target.value)} placeholder={t("title")} autoFocus style={inputStyle} onKeyDown={(e) => { if (e.key === "Enter") createBoardMut.mutate(); }} />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => setAddParent(null)} style={btnStyle}>{t("cancel")}</button>
              <button onClick={() => createBoardMut.mutate()} style={{ ...btnStyle, background: "#3b82f6", color: "#fff", borderColor: "#3b82f6" }}>{t("save")}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
