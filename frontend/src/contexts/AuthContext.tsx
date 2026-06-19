import React, { createContext, useContext, useState, useCallback, ReactNode } from "react";
import { login as apiLogin, logout as apiLogout, AuthResponse, LoginRequest } from "../services/auth";
import { setAccessToken } from "../services/api";

interface User {
  user_id: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function decodeJwtPayload(token: string): { sub: string; role: string } | null {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(atob(base64));
    return { sub: payload.sub || payload.user_id, role: payload.role || "policyholder" };
  } catch {
    return null;
  }
}

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);

  const login = useCallback(async (credentials: LoginRequest) => {
    const response: AuthResponse = await apiLogin(credentials);
    setToken(response.access_token);

    // Decode JWT to get user_id and role
    const payload = decodeJwtPayload(response.access_token);
    if (payload) {
      setUser({ user_id: payload.sub, role: payload.role });
    } else {
      // Fallback: use credentials user_id
      setUser({ user_id: credentials.user_id, role: "policyholder" });
    }
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setToken(null);
    setUser(null);
    setAccessToken(null);
  }, []);

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!token && !!user,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export default AuthContext;
