import api, { setAccessToken } from "./api";

export interface LoginRequest {
  user_id: string;
  password: string;
}

export interface RegisterRequest {
  user_id: string;
  email: string;
  password: string;
  full_name: string;
  phone?: string;
  role?: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export const login = async (credentials: LoginRequest): Promise<AuthResponse> => {
  const response = await api.post<AuthResponse>("/api/auth/login", credentials);
  setAccessToken(response.data.access_token);
  return response.data;
};

export const register = async (data: RegisterRequest): Promise<AuthResponse> => {
  await api.post("/api/auth/register", data);
  // Auto-login after registration
  return login({ user_id: data.user_id, password: data.password });
};

export const logout = async (): Promise<void> => {
  try {
    await api.post("/api/auth/logout");
  } catch {
    // Ignore logout errors
  } finally {
    setAccessToken(null);
  }
};
