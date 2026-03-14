import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/** Cookie name used for app subdomain auth (must match lib/auth.ts). Do not import @/lib/auth here – Edge can't bundle it. */
const AUTH_COOKIE_NAME = "visifoot_session";

/** Host is app subdomain (app.localhost, app.deepfoot.io, etc.) */
function isAppSubdomain(host: string): boolean {
  return host.startsWith("app.");
}

export function middleware(request: NextRequest) {
  const host = request.headers.get("host") ?? "";
  const hostname = host.split(":")[0].toLowerCase();
  if (hostname === "deepfoot.xyz" || hostname === "www.deepfoot.xyz") {
    const url = request.nextUrl.clone();
    url.protocol = "https";
    url.host = "deepfoot.io";
    return NextResponse.redirect(url, 308);
  }
  if (hostname === "app.deepfoot.xyz") {
    const url = request.nextUrl.clone();
    url.protocol = "https";
    url.host = "app.deepfoot.io";
    return NextResponse.redirect(url, 308);
  }

  if (!isAppSubdomain(host)) {
    return NextResponse.next();
  }

  const pathname = request.nextUrl.pathname;

  // Public routes on app subdomain: sign-in, sign-up, analyse (signup funnel), auth callback
  if (
    pathname === "/sign-in" ||
    pathname.startsWith("/sign-in/") ||
    pathname === "/sign-up" ||
    pathname.startsWith("/sign-up/") ||
    pathname === "/analyse" ||
    pathname.startsWith("/analyse/") ||
    pathname === "/auth/callback" ||
    pathname.startsWith("/auth/callback/")
  ) {
    return NextResponse.next();
  }

  // Restrict app subdomain: require auth cookie, else redirect to sign-in
  const hasAuth = request.cookies.get(AUTH_COOKIE_NAME)?.value;
  if (!hasAuth) {
    const signInUrl = request.nextUrl.clone();
    signInUrl.pathname = "/sign-in";
    const nextPath = `${request.nextUrl.pathname}${request.nextUrl.search || ""}`;
    signInUrl.searchParams.set("next", nextPath);
    return NextResponse.redirect(signInUrl);
  }

  // Already under /app → no rewrite
  if (pathname.startsWith("/app")) {
    return NextResponse.next();
  }
  // /analyse and /analyze: rewrite to /app/analyze so one page handles both URLs
  if (pathname === "/analyse" || pathname.startsWith("/analyse/")) {
    const url = request.nextUrl.clone();
    url.pathname = pathname === "/analyse" ? "/app/analyze" : `/app/analyze${pathname.slice(8)}`;
    return NextResponse.rewrite(url);
  }
  if (pathname === "/analyze" || pathname.startsWith("/analyze/")) {
    const url = request.nextUrl.clone();
    url.pathname = pathname === "/analyze" ? "/app/analyze" : `/app/analyze${pathname.slice(8)}`;
    return NextResponse.rewrite(url);
  }
  // Rewrite / → /app, /history → /app/history, etc.
  const rewritePath = pathname === "/" ? "/app" : `/app${pathname}`;
  const url = request.nextUrl.clone();
  url.pathname = rewritePath;
  return NextResponse.rewrite(url);
}

export const config = {
  matcher: [
    /*
     * Match all paths on app subdomain except _next, static files, api.
     * For localhost with port: host is "app.localhost:3000"
     */
    "/((?!_next/static|_next/image|api|favicon.ico|logo.png|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)",
  ],
};
