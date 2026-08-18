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
  editTask: { en: "Edit task", es: "Editar tarea" },
  confirmDelete: { en: "Delete this permanently?", es: "Eliminar esto permanentemente?" },
  moveWarning: { en: "This will move the project and ALL its tasks and sub-projects. It cannot be undone.", es: "Esto movera el proyecto y TODAS sus tareas y sub-proyectos. No se puede deshacer." },
  move: { en: "Move", es: "Mover" },
  moveTo: { en: "to", es: "a" },
  deleteBoardWarning: { en: "Delete this board and ALL its tasks and sub-projects? You can restore it from the Trash within 30 days.", es: "Eliminar este tablero y TODAS sus tareas y sub-proyectos? Puedes restaurarlo desde la Papelera dentro de 30 dias." },
  deleteTaskWarning: { en: "Delete this task? You can restore it from the Trash within 30 days.", es: "Eliminar esta tarea? Puedes restaurarla desde la Papelera dentro de 30 dias." },
  deleteTeamWarning: { en: "Delete this team? Shares given through it will be removed.", es: "Eliminar este equipo? Los accesos compartidos a traves de el se quitaran." },
  deleteStatusWarning: { en: "Delete this status? Tasks using it keep their status text.", es: "Eliminar este estado? Las tareas que lo usan conservan su texto." },
  removeMemberWarning: { en: "Remove this member from the team?", es: "Quitar a este miembro del equipo?" },
  dragHint: { en: "Drag column headers to reorder or move between sections.", es: "Arrastra los encabezados para reordenar o mover entre secciones." },
  selectDestination: { en: "Select destination", es: "Selecciona destino" },
  topLevel: { en: "Top level (own section)", es: "Nivel superior (seccion propia)" },
  convertToProject: { en: "Convert to project", es: "Convertir en proyecto" },
  convertConfirm: { en: "Turn this task into a project? It becomes a board where you can add sub-tasks.", es: "Convertir esta tarea en un proyecto? Se vuelve un tablero donde puedes agregar sub-tareas." },
  sortBy: { en: "Sort", es: "Ordenar" },
  manual: { en: "manual", es: "manual" },
  newestFirst: { en: "newest", es: "recientes" },
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

  company: { en: "Company", es: "Empresa" },
  project: { en: "Project", es: "Proyecto" },
  team: { en: "Team", es: "Equipo" },
  teams: { en: "Teams", es: "Equipos" },
  people: { en: "People", es: "Personas" },
  users: { en: "Users", es: "Usuarios" },
  members: { en: "Members", es: "Miembros" },
  admin: { en: "Admin", es: "Admin" },
  member: { en: "Member", es: "Miembro" },
  addUser: { en: "Add user", es: "Agregar usuario" },
  addTeam: { en: "Add team", es: "Agregar equipo" },
  createTeam: { en: "Create team", es: "Crear equipo" },
  teamName: { en: "Team name", es: "Nombre del equipo" },
  active: { en: "Active", es: "Activo" },
  deactivated: { en: "Deactivated", es: "Desactivado" },
  activate: { en: "Activate", es: "Activar" },
  deactivate: { en: "Deactivate", es: "Desactivar" },
  settings: { en: "Settings", es: "Configuracion" },
  changePassword: { en: "Change password", es: "Cambiar contrasena" },
  currentPassword: { en: "Current password", es: "Contrasena actual" },
  newPassword: { en: "New password", es: "Nueva contrasena" },
  person: { en: "Person", es: "Persona" },
  shareTask: { en: "Share task", es: "Compartir tarea" },
  shareSelected: { en: "Share selected", es: "Compartir seleccionados" },
  saved: { en: "Saved", es: "Guardado" },
  remove: { en: "Remove", es: "Quitar" },
  statuses: { en: "Statuses", es: "Estados" },
  addStatus: { en: "Add status", es: "Agregar estado" },
  newStatusPlaceholder: { en: "New status name (e.g. In Review)", es: "Nombre del nuevo estado (ej. En Revision)" },
  statusesHint: { en: "Statuses appear as Kanban columns and in every status dropdown. Deleting one keeps tasks intact.", es: "Los estados aparecen como columnas Kanban y en cada lista de estados. Eliminar uno no borra tareas." },
  noUsersToAdd: { en: "No other active users yet. Add them in the People tab.", es: "Aun no hay otros usuarios activos. Agregalos en la pestana Personas." },
  noMembers: { en: "No members yet", es: "Sin miembros aun" },
  trash: { en: "Trash", es: "Papelera" },
  restore: { en: "Restore", es: "Restaurar" },
  deleteForever: { en: "Delete forever", es: "Eliminar definitivamente" },
  trashEmpty: { en: "Trash is empty", es: "La papelera esta vacia" },
  trashHint: { en: "Deleted items stay here for 30 days, then they are removed automatically.", es: "Los elementos eliminados permanecen aqui 30 dias, luego se eliminan automaticamente." },
  daysLeft: { en: "days left", es: "dias restantes" },
  convertTo: { en: "Convert to", es: "Convertir a" },
  convertBoardConfirm: { en: "Change this board's level? Tasks and sub-boards come along.", es: "Cambiar el nivel de este tablero? Las tareas y sub-tableros van con el." },
  deleteForeverWarning: { en: "Delete this forever? This cannot be undone.", es: "Eliminar esto definitivamente? No se puede deshacer." },
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
