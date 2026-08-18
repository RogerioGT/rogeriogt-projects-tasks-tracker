import { useState, useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nProvider, useI18n } from "./i18n";
import { AuthProvider, useAuth } from "./auth";
import BoardView from "./views/BoardView";
import KanbanView from "./views/KanbanView";
import ListView from "./views/ListView";
import CompactView from "./views/CompactView";
import DashboardView from "./views/DashboardView";
import HistoryView from "./views/HistoryView";
import AccountDialog from "./components/AccountDialog";

type ViewKey = "board" | "kanban" | "list" | "compact" | "dashboard" | "history";

const qc = new QueryClient({
  defaultOptions: { queries: { staleTime: 10_000, retry: 1 } },
});

function TopBar({
  view,
  setView,
  search,
  setSearch,
}: {
  view: ViewKey;
  setView: (v: ViewKey) => void;
  search: string;
  setSearch: (s: string) => void;
}) {
  const { t, locale, setLocale } = useI18n();
  const { user } = useAuth();
  const [accountOpen, setAccountOpen] = useState(false);
  const [density, setDensity] = useState<"compact" | "cozy">(
    () => (localStorage.getItem("density") as "compact" | "cozy") || "compact",
  );
  const [theme, setTheme] = useState<"dark" | "light">(
    () => (localStorage.getItem("theme") as "dark" | "light") || "dark",
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-density", density);
    localStorage.setItem("density", density);
  }, [density]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  const views: { key: ViewKey; label: string }[] = [
    { key: "board", label: t("board") },
    { key: "kanban", label: t("kanban") },
    { key: "list", label: t("list") },
    { key: "compact", label: t("compact") },
    { key: "dashboard", label: t("dashboard") },
    { key: "history", label: t("history") },
  ];

  return (
    <header
      style={{
        height: 36,
        minHeight: 36,
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "0 10px",
        borderBottom: "1px solid var(--border)",
        background: "var(--bg-surface)",
        position: "sticky",
        top: 0,
        zIndex: 20,
      }}
    >
      <div style={{ fontWeight: 700, fontSize: 11, letterSpacing: 0.3, whiteSpace: "nowrap" }}>{t("appTitle")}</div>

      <div style={{ display: "flex", gap: 2, marginLeft: 12 }}>
        {views.map((v) => (
          <button
            key={v.key}
            onClick={() => setView(v.key)}
            style={{
              fontSize: 11,
              padding: "3px 8px",
              border: "1px solid transparent",
              borderRadius: 4,
              background: view === v.key ? "var(--bg-elevated)" : "transparent",
              color: view === v.key ? "var(--text)" : "var(--text-muted)",
              borderColor: view === v.key ? "var(--border-strong)" : "transparent",
              cursor: "pointer",
              fontWeight: view === v.key ? 600 : 400,
            }}
          >
            {v.label}
          </button>
        ))}
      </div>

      <div style={{ flex: 1 }} />

      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder={t("searchPlaceholder")}
        style={{
          fontSize: 11,
          padding: "4px 8px",
          border: "1px solid var(--border)",
          borderRadius: 4,
          background: "var(--bg)",
          color: "var(--text)",
          width: 180,
          outline: "none",
        }}
      />

      <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
        <button
          onClick={() => setLocale(locale === "en" ? "es" : "en")}
          title="Toggle locale"
          style={{
            fontSize: 11,
            padding: "3px 6px",
            border: "1px solid var(--border)",
            borderRadius: 4,
            background: "var(--bg-elevated)",
            color: "var(--text)",
            cursor: "pointer",
            minWidth: 36,
          }}
        >
          {locale.toUpperCase()}
        </button>

        <button
          onClick={() => setDensity(density === "compact" ? "cozy" : "compact")}
          title="Toggle density"
          style={{
            fontSize: 11,
            padding: "3px 6px",
            border: "1px solid var(--border)",
            borderRadius: 4,
            background: "var(--bg-elevated)",
            color: "var(--text)",
            cursor: "pointer",
          }}
        >
          {density === "compact" ? "Compact" : "Cozy"}
        </button>

        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          title="Toggle theme"
          style={{
            fontSize: 11,
            padding: "3px 6px",
            border: "1px solid var(--border)",
            borderRadius: 4,
            background: "var(--bg-elevated)",
            color: "var(--text)",
            cursor: "pointer",
          }}
        >
          {theme === "dark" ? "Dark" : "Light"}
        </button>

        <button
          onClick={() => setAccountOpen(!accountOpen)}
          title={t("account")}
          style={{
            fontSize: 11,
            padding: "3px 8px",
            border: "1px solid var(--border)",
            borderRadius: 4,
            background: "var(--bg-elevated)",
            color: "var(--text)",
            cursor: "pointer",
            position: "relative",
          }}
        >
          {user ? (user.name || user.email.split("@")[0]) : t("login")}
        </button>
        {accountOpen && (
          <div style={{ position: "absolute", top: 40, right: 10, zIndex: 60 }} onClick={() => setAccountOpen(false)}>
            <AccountDialog onClose={() => setAccountOpen(false)} />
          </div>
        )}
      </div>
    </header>
  );
}

function AppInner() {
  const [view, setView] = useState<ViewKey>("board");
  const [search, setSearch] = useState("");
  const { user, loading, required } = useAuth();

  if (loading) {
    return <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg)", color: "var(--text-muted)", fontSize: 12 }}>Loading...</div>;
  }

  // Required mode with no session → full-screen login gate.
  if (required && !user) {
    return (
      <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg)" }}>
        <AccountDialog onClose={() => {}} />
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden", background: "var(--bg)" }}>
      <TopBar view={view} setView={setView} search={search} setSearch={setSearch} />
      <main style={{ flex: 1, overflow: "auto", background: "var(--bg)" }}>
        {view === "board" && <BoardView search={search} />}
        {view === "kanban" && <KanbanView search={search} />}
        {view === "list" && <ListView search={search} />}
        {view === "compact" && <CompactView search={search} />}
        {view === "dashboard" && <DashboardView />}
        {view === "history" && <HistoryView />}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <I18nProvider>
        <AuthProvider>
          <AppInner />
        </AuthProvider>
      </I18nProvider>
    </QueryClientProvider>
  );
}
