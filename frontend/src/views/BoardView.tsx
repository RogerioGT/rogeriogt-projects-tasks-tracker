import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useVirtualizer } from "@tanstack/react-virtual";
import { fetchBoardTree, fetchTasks, fetchStatuses, createTask, toggleComplete, updateTask, createBoard, updateBoard, moveBoard, deleteBoard, deleteTask, convertTaskToProject, Task, fetchBoards, Board, BoardTreeNode } from "../api";
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
  canEdit,
}: {
  task: Task;
  onToggle: () => void;
  onUpdate: (patch: Partial<Task>) => void;
  onDelete: () => void;
  onShare: () => void;
  onConvert: () => void;
  canEdit: boolean;
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
        <input type="checkbox" checked={task.status === "done"} onChange={onToggle} disabled={!canEdit} style={{ accentColor: "#22c55e", width: 12, height: 12, opacity: canEdit ? 1 : 0.4, cursor: canEdit ? "pointer" : "not-allowed" }} />
        <button
          onClick={() => setOpen(!open)}
          disabled={!canEdit}
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
            <button onClick={() => { if (confirm(t("deleteTaskWarning"))) onDelete(); }} style={{ ...btnStyle, color: "#ef4444", borderColor: "#ef444455" }}>{t("delete")}</button>
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
  allBoards,
  draggedId,
  dropTarget,
  onDragStart,
  onDragEnd,
  onDragOverBoard,
  onDropBoard,
  onDropSection,
}: {
  board: BoardTreeNode;
  tasksAll: Task[];
  depth: number;
  onAddBoard: (parentId: string) => void;
  allBoards: Board[];
  draggedId: string | null;
  dropTarget: { boardId: string; before: boolean } | null;
  onDragStart: (id: string) => void;
  onDragEnd: () => void;
  onDragOverBoard: (boardId: string, before: boolean) => void;
  onDropBoard: (draggedId: string, targetId: string, before: boolean) => void;
  onDropSection: (sectionId: string, before: boolean) => void;
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
  const [moveTarget, setMoveTarget] = useState("");
  const [moveOpen, setMoveOpen] = useState(false);
  const [menuPos, setMenuPos] = useState<{ top: number; right: number } | null>(null);

  const canEdit = board.permission === "edit";

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
  const moveBoardMut = useMutation({
    mutationFn: ({ parentId }: { parentId: string | null }) => moveBoard(board.id, { parent_id: parentId, position: null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["boards"] }); setMoveOpen(false); },
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
  const isDragOver = dropTarget?.boardId === board.id;
  const dropBefore = dropTarget?.before ?? false;
  const draggedIsSection = draggedId ? (allBoards.find((b) => b.id === draggedId)?.parent_id ?? null) === null : false;

  return (
    <div
      draggable={canEdit}
      onDragStart={(e) => {
        if (!canEdit) return;
        e.dataTransfer.setData("text/plain", board.id);
        e.dataTransfer.effectAllowed = "move";
        onDragStart(board.id);
      }}
      onDragEnd={onDragEnd}
      onDragOver={(e) => {
        if (!draggedId || draggedId === board.id || draggedIsSection) return;
        e.preventDefault();
        e.stopPropagation();  // don't let the section container override with 'append to end'
        e.dataTransfer.dropEffect = "move";
        const rect = e.currentTarget.getBoundingClientRect();
        const before = e.clientX < rect.left + rect.width / 2;
        onDragOverBoard(board.id, before);
      }}
      onDrop={(e) => {
        if (draggedIsSection) return;
        e.preventDefault();
        e.stopPropagation();  // column drop wins over section append
        const id = draggedId || e.dataTransfer.getData("text/plain");
        if (id && id !== board.id) onDropBoard(id, board.id, dropBefore);
      }}
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
        opacity: draggedId === board.id ? 0.4 : 1,
        boxShadow: isDragOver ? `inset ${dropBefore ? "3px 0 0" : "0 3px 0 0"} #3b82f6` : undefined,
        cursor: "grab",
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
        {canEdit && (
          <button
            onClick={(e) => {
              const r = e.currentTarget.getBoundingClientRect();
              if (menuOpen) setMenuOpen(false);
              else {
                setMenuPos({ top: r.bottom + 4, right: window.innerWidth - r.right });
                setMenuOpen(true);
              }
            }}
            style={{ fontSize: 12, padding: "2px 6px", border: "1px solid var(--border)", borderRadius: 4, background: "var(--bg)", color: "var(--text-muted)", cursor: "pointer" }}
          >
            ...
          </button>
        )}
        {menuOpen && menuPos && (
          <div
            style={{
              position: "fixed",
              top: Math.min(menuPos.top, window.innerHeight - 260),
              right: menuPos.right,
              background: "var(--bg-elevated)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: 8,
              minWidth: 180,
              zIndex: 90,
              display: "flex",
              flexDirection: "column",
              gap: 6,
              boxShadow: "0 8px 24px rgba(0,0,0,0.5)",
            }}
          >
            <input value={editName} onChange={(e) => setEditName(e.target.value)} style={inputStyle} placeholder={t("title")} />
            <input type="color" value={editColor} onChange={(e) => setEditColor(e.target.value)} style={{ width: "100%", height: 28, border: "1px solid var(--border)", borderRadius: 4, background: "var(--bg)" }} />
            <div style={{ display: "flex", gap: 6 }}>
              <button onClick={() => updateBoardMut.mutate()} style={{ ...btnStyle, flex: 1, background: "#3b82f6", color: "#fff", borderColor: "#3b82f6" }}>{t("save")}</button>
              <button onClick={() => setMenuOpen(false)} style={{ ...btnStyle, flex: 1 }}>{t("cancel")}</button>
            </div>
            <button onClick={() => onAddBoard(board.id)} style={{ ...btnStyle, textAlign: "left" }}>{t("addProject")}</button>
            <button onClick={() => { setMenuOpen(false); setShareOpen(true); }} style={{ ...btnStyle, textAlign: "left" }}>{t("share")}</button>
            <button onClick={() => { setMenuOpen(false); setMoveOpen(true); }} style={{ ...btnStyle, textAlign: "left" }}>{t("move")}...</button>
            <button onClick={() => { if (confirm(t("deleteBoardWarning"))) deleteBoardMut.mutate(); }} style={{ ...btnStyle, color: "#ef4444", borderColor: "#ef444455" }}>{t("delete")}</button>
          </div>
        )}
      </div>

      {canEdit && (
        <form onSubmit={handleAdd} style={{ padding: "6px 6px 4px", borderBottom: "1px solid var(--border)", display: "flex", gap: 4, background: "var(--bg-surface)", position: "sticky", top: 0 }}>
          <input value={newTitle} onChange={(e) => setNewTitle(e.target.value)} placeholder={t("newTaskPlaceholder")} style={{ ...inputStyle, flex: 1 }} />
          <button type="submit" style={{ ...btnStyle, background: board.color, color: "#fff", borderColor: board.color, whiteSpace: "nowrap" }}>{t("addTask")}</button>
        </form>
      )}

      {isNestedParent ? (
        <div style={{ flex: 1, overflow: "auto", padding: 6, display: "flex", flexDirection: "column", gap: 8 }}>
          {board.children.map((child) => (
            <Column key={child.id} board={child} tasksAll={tasksAll} depth={depth + 1} onAddBoard={onAddBoard} allBoards={allBoards} draggedId={draggedId} dropTarget={dropTarget} onDragStart={onDragStart} onDragEnd={onDragEnd} onDragOverBoard={onDragOverBoard} onDropBoard={onDropBoard} onDropSection={onDropSection} />
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
                      <TaskRow task={task} onToggle={() => toggleMut.mutate(task.id)} onUpdate={(patch) => updateMut.mutate({ id: task.id, patch })} onDelete={() => deleteTaskMut.mutate(task.id)} onShare={() => setTaskShareId(task.id)} onConvert={() => { if (confirm(t("convertConfirm"))) convertMut.mutate(task.id); }} canEdit={canEdit} />
                    </div>
                  );
                })}
              </div>
            ) : (
              active.map((task) => (
                <TaskRow key={task.id} task={task} onToggle={() => toggleMut.mutate(task.id)} onUpdate={(patch) => updateMut.mutate({ id: task.id, patch })} onDelete={() => deleteTaskMut.mutate(task.id)} onShare={() => setTaskShareId(task.id)} onConvert={() => { if (confirm(t("convertConfirm"))) convertMut.mutate(task.id); }} canEdit={canEdit} />
              ))
            )}
          </div>

          {done.length > 0 && (
            <div style={{ borderTop: "1px solid var(--border)", background: "var(--bg)", padding: "4px 6px" }}>
              <button onClick={() => setShowCompleted(!showCompleted)} style={{ fontSize: 10, color: "var(--text-muted)", background: "transparent", border: "none", cursor: "pointer", width: "100%", textAlign: "left", padding: "2px 0" }}>
                {showCompleted ? "▾" : "▸"} {t("completed")} ({done.length})
              </button>
              {showCompleted && <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 4, opacity: 0.75 }}>{done.map((task) => (<TaskRow key={task.id} task={task} onToggle={() => toggleMut.mutate(task.id)} onUpdate={(patch) => updateMut.mutate({ id: task.id, patch })} onDelete={() => deleteTaskMut.mutate(task.id)} onShare={() => setTaskShareId(task.id)} onConvert={() => { if (confirm(t("convertConfirm"))) convertMut.mutate(task.id); }} canEdit={canEdit} />))}</div>}
            </div>
          )}
        </>
      )}

      {shareOpen && (
        <div className="modal-overlay" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }} onClick={() => setShareOpen(false)}>
          <ShareDialog scope={{ type: "board", boardId: board.id, boardName: board.name }} onClose={() => setShareOpen(false)} />
        </div>
      )}

      {taskShareId && (
        <div className="modal-overlay" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }} onClick={() => setTaskShareId("")}>
          <ShareDialog scope={{ type: "task", taskIds: [taskShareId], label: "" }} onClose={() => setTaskShareId("")} />
        </div>
      )}

      {moveOpen && (
        <div className="modal-overlay" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }} onClick={() => setMoveOpen(false)}>
          <div onClick={(e) => e.stopPropagation()} style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderRadius: 8, padding: 16, minWidth: 300, display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 700 }}>{t("move")}: {board.name}</div>
            <select value={moveTarget} onChange={(e) => setMoveTarget(e.target.value)} style={inputStyle}>
              <option value="">{t("selectDestination")}</option>
              <option value="__top__">{t("topLevel")}</option>
              {allBoards
                .filter((b) => b.id !== board.id && b.kind !== "project")
                .map((b) => (
                  <option key={b.id} value={b.id}>{b.name}</option>
                ))}
            </select>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => setMoveOpen(false)} style={btnStyle}>{t("cancel")}</button>
              <button
                onClick={() => {
                  if (!moveTarget) return;
                  if (confirm(t("moveWarning"))) moveBoardMut.mutate({ parentId: moveTarget === "__top__" ? null : moveTarget });
                }}
                disabled={!moveTarget}
                style={{ ...btnStyle, background: "#3b82f6", color: "#fff", borderColor: "#3b82f6", opacity: moveTarget ? 1 : 0.5 }}
              >
                {t("move")}
              </button>
            </div>
          </div>
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
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [dropTarget, setDropTarget] = useState<{ boardId: string; before: boolean } | null>(null);
  const [sectionDrop, setSectionDrop] = useState<{ sectionId: string; before: boolean } | null>(null);
  const [sectionDropTarget, setSectionDropTarget] = useState<{ sectionId: string; before: boolean } | null>(null);

  const createBoardMut = useMutation({
    mutationFn: () => createBoard({ name: newBoardName, parent_id: addParent, kind: addParent ? "project" : "section", sort_order: 0 }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["boards"] }); setAddParent(null); setNewBoardName(""); },
  });

  const moveBoardMut = useMutation({
    mutationFn: ({ id, parentId, position }: { id: string; parentId: string | null; position: number | null }) =>
      moveBoard(id, { parent_id: parentId, position }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["boards"] }),
  });

  const boardById = new Map((flatBoards || []).map((b) => [b.id, b]));

  const handleDropBoard = (dragged: string, targetId: string, before: boolean) => {
    const draggedBoard = boardById.get(dragged);
    const targetBoard = boardById.get(targetId);
    if (!draggedBoard || !targetBoard) return;
    const siblings = (flatBoards || []).filter((b) => b.parent_id === targetBoard.parent_id);
    const targetIndex = siblings.findIndex((b) => b.id === targetId);
    let position = targetIndex + (before ? 0 : 1);
    if (draggedBoard.parent_id === targetBoard.parent_id && targetIndex > -1) {
      // same parent: position relative to list without dragged
      const withoutDragged = siblings.filter((b) => b.id !== dragged);
      position = Math.max(0, before ? withoutDragged.findIndex((b) => b.id === targetId) : withoutDragged.findIndex((b) => b.id === targetId) + 1);
    }
    if (draggedBoard.parent_id !== targetBoard.parent_id) {
      const ok = confirm(`${t("moveWarning")}\n\n${t("move")} "${draggedBoard.name}" ${t("moveTo")} "${targetBoard.parent_id === null ? targetBoard.name : (boardById.get(targetBoard.parent_id || "")?.name || "?")}"?`);
      if (!ok) return;
    }
    moveBoardMut.mutate({ id: dragged, parentId: targetBoard.parent_id, position });
  };

  const handleDropSection = (sectionId: string, before: boolean) => {
    const draggedBoard = boardById.get(draggedId || "");
    if (!draggedBoard) return;
    if (draggedBoard.parent_id === null) return;  // sections reorder via the section band, not here
    if (draggedBoard.parent_id !== sectionId) {
      const ok = confirm(`${t("moveWarning")}\n\n${t("move")} "${draggedBoard.name}" ${t("moveTo")} "${boardById.get(sectionId)?.name}"?`);
      if (!ok) return;
    }
    const siblings = (flatBoards || []).filter((b) => b.parent_id === sectionId);
    moveBoardMut.mutate({ id: draggedId as string, parentId: sectionId, position: siblings.length });
  };

  const handleDropSectionReorder = (dragged: string, targetSectionId: string, before: boolean) => {
    const draggedBoard = boardById.get(dragged);
    if (!draggedBoard || dragged === targetSectionId) return;
    const roots = (flatBoards || []).filter((b) => b.parent_id === null);
    const withoutDragged = roots.filter((b) => b.id !== dragged);
    const targetIndex = withoutDragged.findIndex((b) => b.id === targetSectionId);
    const position = before ? targetIndex : targetIndex + 1;
    moveBoardMut.mutate({ id: dragged, parentId: null, position: Math.max(0, position) });
  };

  const addTopSection = () => {
    const name = prompt(t("addSection"));
    if (name?.trim()) createBoard({ name: name.trim(), kind: "section", sort_order: 0 }).then(() => qc.invalidateQueries({ queryKey: ["boards"] }));
  };

  if (!tree || !tasks) return <div style={{ padding: 16, fontSize: 11, color: "var(--text-muted)" }}>Loading...</div>;

  const boardMap = new Map((flatBoards || []).map((b) => [b.id, b]));

  return (
    <div style={{ padding: 8, display: "flex", flexDirection: "column", gap: 10 }}>
      {(tree as BoardTreeNode[]).map((section) => (
        <div
          key={section.id}
          style={{
            border: "1px solid var(--border)",
            borderRadius: 8,
            overflow: "hidden",
            background: "var(--bg-surface)",
            opacity: draggedId === section.id ? 0.4 : 1,
            boxShadow: sectionDropTarget?.sectionId === section.id
              ? `inset 0 ${sectionDropTarget.before ? "3px" : "-3px"} 0 #3b82f6`
              : undefined,
          }}
        >
          <div
            draggable
            onDragStart={(e) => {
              e.dataTransfer.setData("text/plain", section.id);
              e.dataTransfer.effectAllowed = "move";
              setDraggedId(section.id);
            }}
            onDragEnd={() => { setDraggedId(null); setSectionDropTarget(null); setDropTarget(null); setSectionDrop(null); }}
            onDragOver={(e) => {
              if (!draggedId || draggedId === section.id) return;
              const draggedBoard = boardById.get(draggedId);
              const isSectionDrag = draggedBoard?.parent_id === null;
              if (!isSectionDrag) return;  // column drags: let the columns area handle it
              e.preventDefault();
              e.stopPropagation();
              const rect = e.currentTarget.getBoundingClientRect();
              const before = e.clientY < rect.top + rect.height / 2;
              setSectionDropTarget({ sectionId: section.id, before });
            }}
            onDrop={(e) => {
              const draggedBoard = boardById.get(draggedId || "");
              if (!draggedBoard || draggedBoard.parent_id !== null) return;  // only section reorder here
              e.preventDefault();
              e.stopPropagation();
              const id = draggedId || e.dataTransfer.getData("text/plain");
              if (id && id !== section.id) handleDropSectionReorder(id, section.id, sectionDropTarget?.before ?? false);
              setSectionDropTarget(null);
            }}
            style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 10px", background: section.color, color: "#fff", cursor: "grab" }}
          >
            <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: 0.2 }}>{section.name}</span>
            <span style={{ fontSize: 10, background: "rgba(255,255,255,0.2)", padding: "1px 6px", borderRadius: 99 }}>{section.children.length} columns</span>
            <div style={{ flex: 1 }} />
            <button onMouseDown={(e) => e.stopPropagation()} onClick={(e) => { e.stopPropagation(); setAddParent(section.id); }} style={{ fontSize: 11, padding: "2px 8px", borderRadius: 4, border: "1px solid rgba(255,255,255,0.5)", background: "rgba(255,255,255,0.15)", color: "#fff", cursor: "pointer" }}>
              + {t("addColumn")}
            </button>
          </div>

          <div
            style={{ display: "flex", gap: 6, padding: 6, overflowX: "auto", alignItems: "flex-start", minHeight: 120 }}
            onDragOver={(e) => {
              if (!draggedId) return;
              const draggedBoard = boardById.get(draggedId);
              if (draggedBoard?.parent_id === null) return;  // section drags use the band
              e.preventDefault();
              setSectionDrop({ sectionId: section.id, before: false });
            }}
            onDrop={(e) => {
              e.preventDefault();
              handleDropSection(section.id, false);
              setSectionDrop(null);
            }}
            onDragLeave={() => setSectionDrop(null)}
          >
            {section.children.length === 0 ? (
              <div style={{ fontSize: 11, color: "var(--text-faint)", padding: 12 }}>{t("noTasks")} — {t("addColumn")}</div>
            ) : (
              section.children.map((col) => (
                <Column
                  key={col.id}
                  board={col}
                  tasksAll={tasks as Task[]}
                  depth={0}
                  onAddBoard={setAddParent}
                  allBoards={(flatBoards || []) as Board[]}
                  draggedId={draggedId}
                  dropTarget={dropTarget}
                  onDragStart={setDraggedId}
                  onDragEnd={() => { setDraggedId(null); setDropTarget(null); setSectionDrop(null); }}
                  onDragOverBoard={(boardId, before) => setDropTarget({ boardId, before })}
                  onDropBoard={handleDropBoard}
                  onDropSection={handleDropSection}
                />
              ))
            )}
          </div>
        </div>
      ))}

      <div style={{ display: "flex", gap: 8, padding: "4px 2px", flexWrap: "wrap" }}>
        <button onClick={addTopSection} style={{ fontSize: 11, padding: "4px 10px", border: "1px dashed var(--border-strong)", borderRadius: 6, background: "transparent", color: "var(--text-muted)", cursor: "pointer" }}>
          + {t("addSection")}
        </button>
        <span style={{ fontSize: 10, color: "var(--text-faint)", alignSelf: "center" }}>{(flatBoards || []).length} boards · {(tasks as Task[]).length} tasks</span>
        <span style={{ fontSize: 10, color: "var(--text-faint)", alignSelf: "center" }}>{t("dragHint")}</span>
      </div>

      {addParent !== null && (
        <div className="modal-overlay" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }} onClick={() => setAddParent(null)}>
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
