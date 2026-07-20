import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  onAuthStateChanged,
  signInWithPopup,
  signOut,
  type User,
} from "firebase/auth";
import apiClient from "../api/axiosClient";
import { auth, googleProvider } from "../lib/firebase";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  error: string | null;
  isLoginPromptOpen: boolean;
  signInWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  openLoginPrompt: () => void;
  closeLoginPrompt: () => void;
  requireAuth: () => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLoginPromptOpen, setLoginPromptOpen] = useState(false);

  useEffect(() => {
    return onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);
      setLoading(false);

      if (firebaseUser) {
        try {
          await apiClient.post("/auth/firebase");
        } catch (err) {
          console.warn("Backend user sync failed", err);
        }
      }
    });
  }, []);

  const signInWithGoogle = async () => {
    setError(null);
    try {
      await signInWithPopup(auth, googleProvider);
      setLoginPromptOpen(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed";
      if (!message.includes("popup-closed-by-user")) {
        setError("Login Google gagal. Coba lagi sebentar.");
      }
    }
  };

  const logout = async () => {
    await signOut(auth);
  };

  const openLoginPrompt = () => {
    setError(null);
    setLoginPromptOpen(true);
  };

  const closeLoginPrompt = () => setLoginPromptOpen(false);

  const requireAuth = () => {
    if (user) return true;
    openLoginPrompt();
    return false;
  };

  const value = useMemo(
    () => ({
      user,
      loading,
      error,
      isLoginPromptOpen,
      signInWithGoogle,
      logout,
      openLoginPrompt,
      closeLoginPrompt,
      requireAuth,
    }),
    [user, loading, error, isLoginPromptOpen],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
