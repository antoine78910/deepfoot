/** Cookie read by middleware to protect app subdomain */
export const AUTH_COOKIE_NAME = "visifoot_session";
export const AUTH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30; // 30 days

export const AUTH_STORAGE_KEY = "visifoot_logged_in";
export const USER_STORAGE_KEY = "visifoot_user";

export type PlanId = "free" | "starter" | "pro" | "lifetime";

export type UserInfo = {
  displayName: string;
  email: string;
  plan: PlanId;
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
      return data;
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
