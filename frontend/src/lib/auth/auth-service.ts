/**
 * AuthService — swappable interface for login/signup/logout.
 *
 * The real backend (http://127.0.0.1:8000) currently exposes ONLY:
 *   - GET /api/v1/auth/me
 *   - GET /api/v1/auth/profile-check
 *
 * It does NOT expose POST /auth/login or POST /auth/signup yet.
 * To avoid hardcoding fake endpoints, login/signup go through this interface
 * and the default implementation is a clearly-isolated MockAuthAdapter.
 *
 * When the backend ships real endpoints:
 *   1. Implement HttpAuthAdapter using apiFetch.
 *   2. Change ONE import in src/lib/auth/index.ts.
 */
export type AuthCredentials = {
  email: string;
  password: string;
  username?: string;
};

export type AuthResult = {
  token: string;
  user: { email: string; username?: string };
};

export interface AuthService {
  login(creds: AuthCredentials): Promise<AuthResult>;
  signup(creds: AuthCredentials): Promise<AuthResult>;
}
