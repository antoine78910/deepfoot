/** Cookie read by middleware to protect app subdomain */
export const AUTH_COOKIE_NAME = "visifoot_session";
export const AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30; // 30 days

export const AUTH_STORAGE_KEY = "visifoot_logged_in";
export const USER_STORAGE_KEY = "visifoot_user";

export type PlanId = "free" | "starter" | "pro" | "lifetime";

export type UserInfo = {
  id?: string; // Supabase user id (pour X-User-Id et /me)
  displayName: string;
  email: string;
  plan: PlanId;
  /** ISO date when subscription ends (cancel at period end). Plan remains until this date. */
  subscription_ends_at?: string | null;
  /** Whop membership id (for upgrade checkout: pass to get proration when switching plan). */
  whop_membership_id?: string | null;
};

export function setAuthCookie(): void {
  if (typeof document === "undefined") return;
  document.cookie = `${AUTH_COOKIE_NAME}=1; path=/; max-age=${AUTH_COOKIE_MAX_AGE}; SameSite=Lax`;
}

export function clearAuthCookie(): void {
  if (typeof document === "undefined") return;
  document.cookie = `${AUTH_COOKIE_NAME}=; path=/; max-age=0`;
}

export function getUserFromStorage(): UserInfo | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as UserInfo;
    if (data && typeof data.displayName === "string" && typeof data.plan === "string") {
      return { ...data, id: data.id ?? undefined };
    }
  } catch {
    // ignore
  }
  return null;
}

export function setUserInStorage(user: UserInfo): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(AUTH_STORAGE_KEY, "1");
  localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
}

export function clearUserFromStorage(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(AUTH_STORAGE_KEY);
  localStorage.removeItem(USER_STORAGE_KEY);
}

/** Derive display name from email (e.g. anto.delbos@gmail.com → anto.delbos) */
export function displayNameFromEmail(email: string): string {
  return email.split("@")[0]?.trim() || email;
}

const SESSION_ID_KEY = "visifoot_session_id";

/**
 * Clé localStorage pour l’historique des analyses : unique par compte (user.id) ou par session (anon).
 * Évite que deux comptes différents partagent le même historique.
 */
export function getHistoryKey(): string {
  if (typeof window === "undefined") return "visifoot_history";
  const user = getUserFromStorage();
  if (user?.id) return `visifoot_history_${user.id}`;
  try {
    let sid = sessionStorage.getItem(SESSION_ID_KEY);
    if (!sid) {
      sid = crypto.randomUUID();
      sessionStorage.setItem(SESSION_ID_KEY, sid);
    }
    return `visifoot_history_anon_${sid}`;
  } catch {
    return "visifoot_history_anon";
  }
}
