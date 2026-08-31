export const PRODUCTION_APP_ORIGIN = "https://app.deepfoot.io";

/** Absolute OAuth/email callback. Same origin on localhost; always app.deepfoot.io in prod. */
export function resolveAuthCallbackUrl(location: {
  hostname: string;
  protocol: string;
  port?: string;
}): string {
  const hostname = (location.hostname || "").toLowerCase();
  const protocol = location.protocol || "https:";
  const port = location.port ? `:${location.port}` : "";

  if (
    hostname === "deepfoot.io" ||
    hostname === "www.deepfoot.io" ||
    hostname === "app.deepfoot.io"
  ) {
    return `${PRODUCTION_APP_ORIGIN}/auth/callback`;
  }

  return `${protocol}//${hostname}${port}/auth/callback`;
}

/**
 * When NEXT_PUBLIC_APP_ORIGIN is set (e.g. https://app.deepfoot.io), all app links use it.
 * Otherwise we use relative /app paths for same-origin.
 * Production: when on deepfoot.io we always use PRODUCTION_APP_ORIGIN so env typos don't break links.
 */
function getAppOrigin(): string | null {
  if (typeof window !== "undefined") {
    const h = window.location.hostname;
    if (h === "app.deepfoot.io") return window.location.origin;
    if (h === "deepfoot.io" || h === "www.deepfoot.io") return PRODUCTION_APP_ORIGIN;
    if (h === "app.localhost") return window.location.origin;
  }
  if (typeof process === "undefined") return null;
  let origin = (process.env.NEXT_PUBLIC_APP_ORIGIN || "").trim().replace(/\/$/, "");
  if (!origin || !origin.startsWith("http")) return null;
  if (origin.includes("localhost") || origin.includes("127.0.0.1")) {
    if (typeof window !== "undefined" && window.location.hostname.includes("deepfoot.io")) {
      return PRODUCTION_APP_ORIGIN;
    }
  }
  if (origin.includes("deepfoot")) {
    if (origin.includes("deepfoot.a") || !origin.includes("deepfoot.io")) {
      origin = PRODUCTION_APP_ORIGIN;
    }
  }
  return origin;
}

export function getAppHref(path: string = ""): string {
  const origin = getAppOrigin();
  const p = path.startsWith("/") ? path : `/${path}`;
  return origin ? `${origin}${p}` : `/app${p === "/" ? "" : p}`;
}

/** Public analyse page lives at /analyse (and on app origin at /analyse as well). */
export function getAnalyseHref(): string {
  const origin = getAppOrigin();
  if (origin) return `${origin}/analyse`;

  // Local dev convenience: from http://localhost:3000, send users to http://app.localhost:3000/analyse
  // so middleware can route them to sign-in/signup on the app host.
  if (typeof window !== "undefined") {
    const { protocol, hostname, port } = window.location;
    if (hostname === "localhost" || hostname === "127.0.0.1") {
      const p = port ? `:${port}` : "";
      return `${protocol}//app.localhost${p}/analyse`;
    }
  }
  return "/analyse";
}

export const APP_HREF = getAppHref("/");

/** App root URL (for redirect after sign-in). In dev on localhost, use app subdomain. */
export function getAppRootUrl(): string {
  const origin = getAppOrigin();
  if (origin) return `${origin}/`;
  if (typeof window !== "undefined") {
    const { protocol, hostname, port } = window.location;
    if (hostname === "localhost" || hostname === "127.0.0.1") {
      const p = port ? `:${port}` : "";
      return `${protocol}//app.${hostname}${p}/`;
    }
  }
  return "/app";
}

/** OAuth / email confirmation callback. Never send a relative URL (Supabase would fall back to Site URL). */
export function getAppAuthCallbackUrl(): string {
  if (typeof window !== "undefined") {
    return resolveAuthCallbackUrl({
      hostname: window.location.hostname,
      protocol: window.location.protocol,
      port: window.location.port,
    });
  }
  return `${PRODUCTION_APP_ORIGIN}/auth/callback`;
}
// Sign-in / sign-up are public routes on the same origin.
export const SIGN_IN_HREF = "/sign-in";
export const SIGN_UP_HREF = "/sign-up";
export const ANALYSE_HREF = getAnalyseHref();
export const MATCHES_HREF = getAppHref("/matches");
