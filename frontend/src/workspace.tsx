import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchWorkspaces, Workspace } from "./api";

/** Current 'main board' selection, persisted to localStorage. */
type WorkspaceCtx = {
  workspaces: Workspace[];
  currentId: string | null;
  current: Workspace | null;
  setCurrentId: (id: string) => void;
  refresh: () => void;
};

const Ctx = createContext<WorkspaceCtx | null>(null);

const LS_KEY = "tt_workspace_id";

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const qc = useQueryClient();
  const { data: workspaces } = useQuery({ queryKey: ["workspaces"], queryFn: fetchWorkspaces });
  const [storedId, setStoredId] = useState<string>(() => localStorage.getItem(LS_KEY) || "");

  const list = workspaces || [];
  const current =
    list.find((w) => w.id === storedId) || (list.length ? list[0] : null);

  // if the stored id vanishes (deleted elsewhere), keep storage in sync
  useEffect(() => {
    if (current && current.id !== storedId) {
      localStorage.setItem(LS_KEY, current.id);
      setStoredId(current.id);
    }
  }, [current, storedId]);

  const value = useMemo<WorkspaceCtx>(
    () => ({
      workspaces: list,
      currentId: current ? current.id : null,
      current,
      setCurrentId: (id: string) => {
        localStorage.setItem(LS_KEY, id);
        setStoredId(id);
      },
      refresh: () => qc.invalidateQueries({ queryKey: ["workspaces"] }),
    }),
    [list, current, qc],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useWorkspace(): WorkspaceCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return ctx;
}
