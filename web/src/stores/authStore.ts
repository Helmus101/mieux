import { create } from 'zustand';
import { api } from '../api/client';

interface AuthState {
  token: string | null;
  sessionId: string | null;
  user: { id: string } | null;
  isAuthenticated: boolean;
  setToken: (token: string) => void;
  setSessionId: (sessionId: string) => void;
  setUser: (user: { id: string }) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  sessionId: null,
  user: null,
  isAuthenticated: false,

  setToken: (token) => {
    set({ token, isAuthenticated: true });
    api.setToken(token);
  },

  setSessionId: (sessionId) => {
    set({ sessionId });
    api.setSessionId(sessionId);
  },

  setUser: (user) => set({ user }),

  login: async (email, password) => {
    const response = await api.login({ email, password });
    set({
      token: response.access_token,
      user: { id: response.user_id },
      isAuthenticated: true,
    });
    api.setToken(response.access_token);
  },

  register: async (email, password) => {
    const response = await api.register({ email, password });
    set({
      token: response.access_token,
      user: { id: response.user_id },
      isAuthenticated: true,
    });
    api.setToken(response.access_token);
  },

  logout: () => {
    set({ token: null, sessionId: null, user: null, isAuthenticated: false });
    api.clearAuth();
  },
}));
