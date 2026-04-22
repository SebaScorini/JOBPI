import React, { createContext, useContext, useState, useEffect } from 'react';
import { Session } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';
import { User } from '../types';
import { apiService, authStorage } from '../services/api';

interface AuthContextType {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  updatePassword: (newPassword: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    // Get the initial session from Supabase (persisted in localStorage)
    supabase.auth.getSession().then(({ data: { session: currentSession } }) => {
      if (cancelled) return;
      setSession(currentSession);

      if (currentSession?.access_token) {
        // Fetch the app-level user profile from our backend
        apiService
          .getMe(currentSession.access_token)
          .then((userData) => {
            if (!cancelled) setUser(userData);
          })
          .catch((error) => {
            console.warn('Failed to fetch user profile:', error);
            if (!cancelled) setUser(null);
          })
          .finally(() => {
            if (!cancelled) setIsLoading(false);
          });
      } else {
        const legacyToken = authStorage.getToken();

        if (legacyToken) {
          apiService
            .getMe(legacyToken)
            .then((userData) => {
              if (!cancelled) setUser(userData);
            })
            .catch((error) => {
              console.warn('Failed to fetch legacy user profile:', error);
              if (!cancelled) {
                authStorage.clearToken();
                setUser(null);
              }
            })
            .finally(() => {
              if (!cancelled) setIsLoading(false);
            });
          return;
        }

        setIsLoading(false);
      }
    });

    // Listen for auth state changes (login, logout, token refresh)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, newSession) => {
      if (cancelled) return;
      setSession(newSession);

      if (newSession?.access_token) {
        try {
          const userData = await apiService.getMe(newSession.access_token);
          if (!cancelled) setUser(userData);
        } catch {
          if (!cancelled) setUser(null);
        }
      } else {
        setUser(null);
      }
    });

    return () => {
      cancelled = true;
      subscription.unsubscribe();
    };
  }, []);

  const login = async (email: string, password: string) => {
    authStorage.clearToken();

    let supabaseError: Error | null = null;
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (error) throw error;
      return;
    } catch (err: unknown) {
      supabaseError = err instanceof Error ? err : new Error(String(err));
    }

    // Only attempt legacy auth when Supabase doesn't recognise the user at all.
    // Wrong passwords, rate-limits, and network errors are NOT reasons to fall
    // back — doing so would consume a second rate-limit counter and produce
    // misleading error messages.
    const supabaseMsg = supabaseError?.message?.toLowerCase() ?? '';
    const isUserNotInSupabase =
      supabaseMsg.includes('invalid login credentials') ||
      supabaseMsg.includes('user not found') ||
      supabaseMsg.includes('email not confirmed');

    if (!isUserNotInSupabase) {
      throw supabaseError;
    }

    try {
      const legacyToken = await apiService.loginWithLegacyAuth(email, password);
      authStorage.setToken(legacyToken);
      const userData = await apiService.getMe(legacyToken);
      setUser(userData);
      setSession(null);
    } catch {
      // Legacy auth also failed — surface the original Supabase error so the
      // user sees a consistent, accurate message rather than a backend error
      // from the legacy system they may not even have an account in.
      throw supabaseError;
    }
  };

  const register = async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
    });
    if (error) throw error;
  };

  const logout = async () => {
    authStorage.clearToken();
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
    setUser(null);
    setSession(null);
  };

  const resetPassword = async (email: string) => {
    const siteUrl =
      typeof window !== 'undefined' && window.location.origin
        ? window.location.origin
        : import.meta.env.VITE_SITE_URL;
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${siteUrl}/reset-password`,
    });
    if (error) throw error;
  };

  const updatePassword = async (newPassword: string) => {
    const { error } = await supabase.auth.updateUser({
      password: newPassword,
    });
    if (error) throw error;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        isLoading,
        login,
        register,
        logout,
        resetPassword,
        updatePassword,
      }}
    >
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
