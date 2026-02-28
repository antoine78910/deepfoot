import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | null = null;

declare global {
  interface Window {
    __SUPABASE_ENV__?: { url: string; anonKey: string };
  }
}

function getSupabaseUrl(): string {
  if (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_SUPABASE_URL) {
    return process.env.NEXT_PUBLIC_SUPABASE_URL;
  }
  if (typeof window !== "undefined" && window.__SUPABASE_ENV__?.url) {
    return window.__SUPABASE_ENV__.url;
  }
  throw new Error(
    "Missing NEXT_PUBLIC_SUPABASE_URL. Copy frontend/.env.example to .env.local, add your Supabase project URL (Dashboard → Settings → API), then restart: npm run dev"
  );
}

function getSupabaseAnonKey(): string {
  if (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
    return process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  }
  if (typeof window !== "undefined" && window.__SUPABASE_ENV__?.anonKey) {
    return window.__SUPABASE_ENV__.anonKey;
  }
  throw new Error(
    "Missing NEXT_PUBLIC_SUPABASE_ANON_KEY. Copy frontend/.env.example to .env.local, add your Supabase anon key (Dashboard → Settings → API), then restart: npm run dev"
  );
}

export function getSupabaseBrowserClient(): SupabaseClient {
  if (client) return client;

  const url = getSupabaseUrl();
  const anonKey = getSupabaseAnonKey();

  client = createClient(url, anonKey, {
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: false, // we handle PKCE exchange in /auth/callback
    },
  });

  return client;
}

