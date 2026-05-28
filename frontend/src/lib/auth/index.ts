import type { AuthService } from "./auth-service";
import { supabaseAuthAdapter } from "./supabase-adapter";

// Swap this export when the backend ships real login/signup endpoints.
export const authService: AuthService = supabaseAuthAdapter;
export type { AuthService, AuthCredentials, AuthResult } from "./auth-service";
