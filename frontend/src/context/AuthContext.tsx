import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types';
import { apiService, authStorage } from '../services/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(authStorage.getToken());
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Use a flag to handle React StrictMode's double-invocation in dev
    let cancelled = false;

    async function loadUser() {
      const storedToken = authStorage.getToken();
      if (!storedToken) {
        setIsLoading(false);
        return;
      }

      try {
        const userData = await apiService.getMe(storedToken);
        if (!cancelled) setUser(userData);
      } catch (error: unknown) {
        if (!cancelled) {
          const status = error instanceof Error && 'status' in error
            ? (error as { status?: number }).status
            : undefined;

          if (status === 401 || status === 403) {
            // Token is invalid/expired — clear session
            console.warn('Session expired. Logging out.');
            authStorage.clearToken();
            setToken(null);
            setUser(null);
          } else {
            // Network error or server down — keep token, let user retry
            console.warn('Backend unreachable. Keeping session.', error);
          }
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadUser();
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = (newToken: string, userData: User) => {
    setToken(newToken);
    setUser(userData);
    authStorage.setToken(newToken);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    authStorage.clearToken();
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
