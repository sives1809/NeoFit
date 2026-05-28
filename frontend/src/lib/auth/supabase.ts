import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "https://placeholder-so-ssr-does-not-crash.supabase.co";
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || "placeholder_key";

// We no longer throw an error on load to prevent full SSR crashes when env vars are missing
// Instead, Supabase will simply fail gracefully during login attempts if these remain placeholders.
export const supabase = createClient(supabaseUrl, supabaseAnonKey);
