import { apiFetch } from "./client";

export type AuthUser = {
  id?: string;
  email?: string;
  username?: string;
  [k: string]: unknown;
};

export type ProfileCheck = {
  has_profile: boolean;
  [k: string]: unknown;
};

export const authApi = {
  me: () => apiFetch<AuthUser>("/auth/me"),
  profileCheck: () => apiFetch<ProfileCheck>("/auth/profile-check"),
};
