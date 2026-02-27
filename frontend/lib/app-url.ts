/**
 * When NEXT_PUBLIC_APP_ORIGIN is set (e.g. https://app.deepfoot.ai), all app links use it.
 * Otherwise we use relative /app paths for same-origin.
 */
function getAppOrigin(): string | null {
  if (typeof process === "undefined") return null;
  const origin = process.env.NEXT_PUBLIC_APP_ORIGIN;
  return origin && origin.startsWith("http") ? origin.replace(/\/$/, "") : null;
}

export function getAppHref(path: string = ""): string {
  const origin = getAppOrigin();
  const p = path.startsWith("/") ? path : `/${path}`;
  return origin ? `${origin}${p}` : `/app${p === "/" ? "" : p}`;
}

export const APP_HREF = getAppHref("/");
export const SIGN_IN_HREF = getAppHref("/sign-in");
export const ANALYSE_HREF = getAppHref("/analyse");
export const MATCHES_HREF = getAppHref("/matches");
