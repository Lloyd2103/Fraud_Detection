import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi, setAuthToken } from '../api';

const AuthContext = createContext(null);

function isJwtExpired(tokenStr) {
  if (!tokenStr) return true;
  try {
    const parts = tokenStr.split('.');
    if (parts.length !== 3) return true;
    const payload = JSON.parse(atob(parts[1]));
    if (!payload.exp) return false;
    return Date.now() >= (payload.exp * 1000 - 5000);
  } catch (_) {
    return true;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => {
    const saved = localStorage.getItem('access_token');
    if (!saved || isJwtExpired(saved)) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_info');
      return null;
    }
    return saved;
  });

  const [user, setUser] = useState(() => {
    try {
      const savedUser = localStorage.getItem('user_info');
      return savedUser ? JSON.parse(savedUser) : null;
    } catch (_) {
      return null;
    }
  });

  const [loading, setLoading] = useState(() => {
    const saved = localStorage.getItem('access_token');
    return Boolean(saved && !isJwtExpired(saved));
  });

  const [error, setError] = useState(null);

  useEffect(() => {
    if (token) {
      setAuthToken(token);
      localStorage.setItem('access_token', token);
    } else {
      setAuthToken(null);
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_info');
    }
  }, [token]);

  useEffect(() => {
    const verifySession = async () => {
      const currentToken = token || localStorage.getItem('access_token');
      if (!currentToken || isJwtExpired(currentToken)) {
        setToken(null);
        setUser(null);
        localStorage.removeItem('access_token');
        localStorage.removeItem('user_info');
        localStorage.removeItem('last_active_tab');
        localStorage.removeItem('last_user_id');
        sessionStorage.removeItem('last_active_tab');
        setLoading(false);
        return;
      }

      try {
        const res = await authApi.getMe(currentToken);
        setUser(res.data);
        localStorage.setItem('user_info', JSON.stringify(res.data));
      } catch (err) {
        if (err.response?.status === 401) {
          setToken(null);
          setUser(null);
          localStorage.removeItem('access_token');
          localStorage.removeItem('user_info');
          localStorage.removeItem('last_active_tab');
          localStorage.removeItem('last_user_id');
          sessionStorage.removeItem('last_active_tab');
        }
      } finally {
        setLoading(false);
      }
    };

    verifySession();
  }, []);

  useEffect(() => {
    if (!token || !user) return;

    const checkRoleLatest = async () => {
      const currentToken = token || localStorage.getItem('access_token');
      if (!currentToken || isJwtExpired(currentToken)) return;
      try {
        const res = await authApi.getMe(currentToken);
        const latestUser = res.data;
        if (latestUser && latestUser.role) {
          setUser((prev) => {
            if (!prev) return latestUser;
            if (prev.role !== latestUser.role || prev.status !== latestUser.status) {
              localStorage.setItem('user_info', JSON.stringify(latestUser));
              return latestUser;
            }
            return prev;
          });
        }
      } catch (_) {
        // network/server glitch does not drop auth state
      }
    };

    window.addEventListener('focus', checkRoleLatest);
    const interval = setInterval(checkRoleLatest, 30000);

    return () => {
      window.removeEventListener('focus', checkRoleLatest);
      clearInterval(interval);
    };
  }, [token, user]);

  const login = useCallback(async (username, password) => {
    setError(null);
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const res = await authApi.login(formData);

    const accessToken = res.data.access_token;
    const userData = res.data.user;

    setToken(accessToken);
    setUser(userData);
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('user_info', JSON.stringify(userData));
    localStorage.setItem('last_user_id', String(userData.id));
    localStorage.removeItem('last_active_tab');
    sessionStorage.removeItem('last_active_tab');
    setAuthToken(accessToken);

    return userData;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      /* ignore */
    }
    setToken(null);
    setUser(null);
    setAuthToken(null);
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_info');
    localStorage.removeItem('last_active_tab');
    localStorage.removeItem('last_user_id');
    sessionStorage.removeItem('last_active_tab');
  }, []);

  const register = useCallback(async (payload) => {
    const res = await authApi.register(payload);
    return res.data;
  }, []);

  const forgotPassword = useCallback(async (email) => {
    const res = await authApi.forgotPassword(email);
    return res.data;
  }, []);

  const verifyOtp = useCallback(async (payload) => {
    const res = await authApi.verifyOtp(payload);
    return res.data;
  }, []);

  const resetPassword = useCallback(async (payload) => {
    const res = await authApi.resetPassword(payload);
    return res.data;
  }, []);

  return (
    <AuthContext.Provider value={{
      user,
      token,
      loading,
      error,
      setError,
      login,
      logout,
      register,
      forgotPassword,
      verifyOtp,
      resetPassword,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
};

export default AuthContext;
