import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { getToken, setToken, fetchMe, login as apiLogin, register as apiRegister, User } from "./api";

type AuthCtx = {
  user: User | null;
  loading: boolean;
  required: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, name: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: (u: User) => void;
};

const AuthContext = createContext<AuthCtx>({
  user: null,
  loading: true,
  required: false,
  login: async () => {},
  register: async () => {},
  logout: () => {},
  refreshUser: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [required, setRequired] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const req = await fetch("/api/auth/required").then((r) => r.json());
        setRequired(!!req.required);
        if (!req.required) {
          // Local mode — no login needed, app works against the local pseudo-user.
          setLoading(false);
          return;
        }
        // Required mode — resolve the user from a stored token.
        if (getToken()) {
          try {
            setUser(await fetchMe());
          } catch {
            setToken(null);
          }
        }
      } catch {
        setRequired(false);
      }
      setLoading(false);
    })();
  }, []);

  const login = async (email: string, password: string) => {
    const r = await apiLogin({ email, password });
    setToken(r.token);
    setUser(r.user);
  };
  const register = async (email: string, name: string, password: string) => {
    const r = await apiRegister({ email, name, password });
    setToken(r.token);
    setUser(r.user);
  };
  const logout = () => {
    setToken(null);
    setUser(null);
  };
  const refreshUser = (u: User) => setUser(u);

  return <AuthContext.Provider value={{ user, loading, required, login, register, logout, refreshUser }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
