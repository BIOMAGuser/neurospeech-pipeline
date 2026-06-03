"use client";

import { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { AuthService } from "@/services/auth";
import { useToast } from "@/hooks/use-toast";
import { Loader2 } from "lucide-react";

interface AuthContextValue {
  isAuthenticated: boolean;
  isAdmin: boolean;
  username: string | null;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();
  const warningTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const logoutTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const logout = useCallback(() => {
    AuthService.logout();
    setIsAuthenticated(false);
    router.replace("/login");
  }, [router]);

  useEffect(() => {
    const valid = AuthService.isTokenValid();
    if (valid) {
      setIsAuthenticated(true);
      setLoading(false);

      const exp = AuthService.getTokenExpiry();
      if (exp) {
        const nowSec = Date.now() / 1000;
        const msUntilExpiry = (exp - nowSec) * 1000;
        const msUntilWarning = msUntilExpiry - 5 * 60 * 1000;

        if (msUntilWarning > 0) {
          warningTimerRef.current = setTimeout(() => {
            toast({
              title: "Sitzung läuft ab",
              description: "Ihre Sitzung läuft in 5 Minuten ab. Bitte speichern Sie Ihre Arbeit.",
              variant: "destructive",
            });
          }, msUntilWarning);
        }

        if (msUntilExpiry > 0) {
          logoutTimerRef.current = setTimeout(() => {
            logout();
          }, msUntilExpiry);
        }
      }
    } else {
      router.replace("/login");
    }

    return () => {
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
      if (logoutTimerRef.current) clearTimeout(logoutTimerRef.current);
    };
  }, [router, toast, logout]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin mr-2" /> Lade...
      </div>
    );
  }

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isAdmin: AuthService.isAdmin(),
        username: AuthService.getUsername(),
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
