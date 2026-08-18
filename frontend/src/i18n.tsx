import { createContext, useContext, useEffect, useState, ReactNode } from "react";

export type Locale = "en" | "es";

type Dict = Record<string, Record<Locale, string>>;

const dict: Dict = {
  appTitle: { en: "Rogerio Projects & Tasks Tracker", es: "Seguimiento de Proyectos y Tareas" },
  board: { en: "Board", es: "Tablero" },
  kanban: { en: "Kanban", es: "Kanban" },
  list: { en: "List", es: "Lista" },
  compact: { en: "Compact", es: "Compacta" },
  dashboard: { en: "Dashboard", es: "Panel" },
  history: { en: "History", es: "Historial" },
  all: { en: "All", es: "Todo" },
  tasks: { en: "Tasks", es: "Tareas" },
  boards: { en: "Boards", es: "Tableros" },
  noHistory: { en: "No activity yet", es: "Sin actividad aun" },

  not_started: { en: "Not started", es: "No iniciado" },
  in_progress: { en: "In progress", es: "En progreso" },
  waiting: { en: "Waiting", es: "En espera" },
  done: { en: "Done", es: "Completado" },

  high: { en: "High", es: "Alta" },
  medium: { en: "Medium", es: "Media" },
  low: { en: "Low", es: "Baja" },
  none: { en: "None", es: "Ninguna" },

  newTaskPlaceholder: { en: "New task...", es: "Nueva tarea..." },
  addTask: { en: "Add task", es: "Agregar tarea" },
  completed: { en: "Completed", es: "Completadas" },
  search: { en: "Search", es: "Buscar" },
  searchPlaceholder: { en: "Search tasks...", es: "Buscar tareas..." },
  sort: { en: "Sort", es: "Ordenar" },
  filter: { en: "Filter", es: "Filtrar" },
  dueDate: { en: "Due date", es: "Fecha limite" },
  assignee: { en: "Assignee", es: "Responsable" },
  priority: { en: "Priority", es: "Prioridad" },
  status: { en: "Status", es: "Estado" },
  noTasks: { en: "No tasks", es: "Sin tareas" },
  save: { en: "Save", es: "Guardar" },
  cancel: { en: "Cancel", es: "Cancelar" },
  delete: { en: "Delete", es: "Eliminar" },
  addSection: { en: "Add section", es: "Agregar seccion" },
  addCompany: { en: "Add company", es: "Agregar empresa" },
  addProject: { en: "Add project", es: "Agregar proyecto" },
  addColumn: { en: "Add column", es: "Agregar columna" },
  rename: { en: "Rename", es: "Renombrar" },
  recolor: { en: "Recolor", es: "Cambiar color" },
  archive: { en: "Archive", es: "Archivar" },
  newTaskBtn: { en: "+ New task", es: "+ Nueva tarea" },
  description: { en: "Description", es: "Descripcion" },
  tags: { en: "Tags", es: "Etiquetas" },
  title: { en: "Title", es: "Titulo" },
  boardLabel: { en: "Board", es: "Tablero" },
  total: { en: "Total", es: "Total" },
  completionRate: { en: "Completion rate", es: "Tasa de completadas" },
  tasksPerStatus: { en: "Tasks per status", es: "Tareas por estado" },
  tasksPerPriority: { en: "Tasks per priority", es: "Tareas por prioridad" },
  tasksPerSection: { en: "Tasks per section", es: "Tareas por seccion" },
  quickAdd: { en: "Quick add", es: "Agregar rapido" },
  allBoards: { en: "All boards", es: "Todos los tableros" },
  showCompleted: { en: "Show completed", es: "Mostrar completadas" },
  hideCompleted: { en: "Hide completed", es: "Ocultar completadas" },

  account: { en: "Account", es: "Cuenta" },
  login: { en: "Log in", es: "Iniciar sesion" },
  register: { en: "Register", es: "Registrarse" },
  logout: { en: "Log out", es: "Cerrar sesion" },
  email: { en: "Email", es: "Correo" },
  password: { en: "Password", es: "Contrasena" },
  name: { en: "Name", es: "Nombre" },
  noAccount: { en: "No account? Register", es: "Sin cuenta? Registrate" },
  haveAccount: { en: "Have an account? Log in", es: "Tienes cuenta? Inicia sesion" },
  share: { en: "Share", es: "Compartir" },
  sharedWith: { en: "Shared with", es: "Compartido con" },
  selectUser: { en: "Select user", es: "Seleccionar usuario" },
  edit: { en: "Edit", es: "Editar" },
  view: { en: "View", es: "Ver" },
  close: { en: "Close", es: "Cerrar" },
};

export type TKey = keyof typeof dict;

type I18nCtx = {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (k: string) => string;
};

const I18nContext = createContext<I18nCtx>({
  locale: "en",
  setLocale: () => {},
  t: (k) => k,
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    const v = localStorage.getItem("locale");
    return v === "es" ? "es" : "en";
  });

  const setLocale = (l: Locale) => {
    setLocaleState(l);
    localStorage.setItem("locale", l);
  };

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const t = (key: string) => {
    const entry = dict[key];
    if (entry) return entry[locale];
    return key;
  };

  return <I18nContext.Provider value={{ locale, setLocale, t }}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}
