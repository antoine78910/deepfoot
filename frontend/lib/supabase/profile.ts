import { getSupabaseBrowserClient } from "./client";

/** Create a free profile if missing. Safe to call after email or Google sign-in. */
export async function ensureUserProfile(userId: string | undefined): Promise<void> {
  if (!userId) return;
  try {
    const supabase = getSupabaseBrowserClient();
    const { data } = await supabase.from("profiles").select("id").eq("id", userId).maybeSingle();
    if (data?.id) return;
    await supabase.from("profiles").insert({ id: userId, plan: "free" });
  } catch {
    // Table missing or RLS — auth still proceeds; backend upserts later.
  }
}
