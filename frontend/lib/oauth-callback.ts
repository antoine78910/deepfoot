import { PRODUCTION_APP_ORIGIN } from "./app-url";

export function isAppAuthHost(hostname: string): boolean {
  const h = (hostname || "").toLowerCase().split(":")[0];
  return h === "app.deepfoot.io" || h === "app.localhost" || h.startsWith("app.");
}

export function isOAuthCallbackParams(searchParams: URLSearchParams): boolean {
  return Boolean(
    searchParams.get("code") ||
      searchParams.get("error") ||
      searchParams.get("error_code")
  );
}

/** Reject open redirects and next= values that replay a failed OAuth query. */
export function sanitizeNextPath(raw: string | null | undefined): string | null {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) return null;
  if (raw.includes("error=") || raw.includes("error_code=") || raw.includes("code=")) return null;
  return raw;
}

/** If Google OAuth starts on the marketing host, hop to the app host first (PKCE is origin-bound). */
export function oauthHopHref(opts: {
  hostname: string;
  kind: "sign-in" | "sign-up";
  next?: string | null;
  port?: string;
}): string | null {
  if (isAppAuthHost(opts.hostname)) return null;
  const path = opts.kind === "sign-up" ? "/sign-up" : "/sign-in";
  const params = new URLSearchParams({ oauth: "google" });
  const next = sanitizeNextPath(opts.next ?? null);
  if (next) params.set("next", next);
  const h = (opts.hostname || "").toLowerCase().split(":")[0];
  const origin =
    h === "localhost" || h === "127.0.0.1"
      ? `http://app.localhost${opts.port ? `:${opts.port}` : ":3000"}`
      : PRODUCTION_APP_ORIGIN;
  return `${origin}${path}?${params}`;
}

/** Supabase Redirect URLs must match this exactly — no ?next= query string. */
export function oauthRedirectTo(origin: string): string {
  return `${origin.replace(/\/$/, "")}/auth/callback`;
}

const OAUTH_NEXT_KEY = "df_oauth_next";
const GOOGLE_OAUTH_LOCK = "df_google_oauth_lock";

export function stashOAuthNext(next: string | null | undefined): void {
  if (typeof sessionStorage === "undefined") return;
  const safe = sanitizeNextPath(next ?? null);
  if (safe) sessionStorage.setItem(OAUTH_NEXT_KEY, safe);
  else sessionStorage.removeItem(OAUTH_NEXT_KEY);
}

export function takeOAuthNext(): string | null {
  if (typeof sessionStorage === "undefined") return null;
  const v = sessionStorage.getItem(OAUTH_NEXT_KEY);
  sessionStorage.removeItem(OAUTH_NEXT_KEY);
  return sanitizeNextPath(v);
}

export function claimGoogleOAuthStart(): boolean {
  if (typeof sessionStorage === "undefined") return true;
  const raw = sessionStorage.getItem(GOOGLE_OAUTH_LOCK);
  if (raw) {
    const started = Number(raw);
    if (Number.isFinite(started) && Date.now() - started < 8000) return false;
  }
  sessionStorage.setItem(GOOGLE_OAUTH_LOCK, String(Date.now()));
  return true;
}

export function clearGoogleOAuthLock(): void {
  if (typeof sessionStorage === "undefined") return;
  sessionStorage.removeItem(GOOGLE_OAUTH_LOCK);
}
