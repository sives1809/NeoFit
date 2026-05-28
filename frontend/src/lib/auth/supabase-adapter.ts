import type { AuthCredentials, AuthResult, AuthService } from "./auth-service";
import { supabase } from "./supabase";

export const supabaseAuthAdapter: AuthService = {
  async login({ email, password }) {
    if (!email || !password) throw new Error("Email and password are required");

    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      throw new Error(error.message);
    }

    if (!data.session) {
      throw new Error("Login failed: No session returned.");
    }

    return {
      token: data.session.access_token,
      user: {
        email: data.user?.email ?? email,
        username: data.user?.user_metadata?.username,
      },
    };
  },

  async signup({ email, password, username }) {
    if (!email || !password) throw new Error("Email and password are required");

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          username: username,
        },
      },
    });

    if (error) {
      throw new Error(error.message);
    }

    if (!data.session) {
      // Sometimes signup requires email confirmation and doesn't return a session immediately.
      // If the app requires immediate login, you might need to handle this differently.
      throw new Error("Signup successful, but please verify your email to log in.");
    }

    return {
      token: data.session.access_token,
      user: {
        email: data.user?.email ?? email,
        username: data.user?.user_metadata?.username ?? username,
      },
    };
  },
};
