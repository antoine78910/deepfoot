import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { AUTH_COOKIE_NAME } from "@/lib/auth";

/** Host is app subdomain (app.localhost, app.deepfoot.ai, etc.) */
function isAppSubdomain(host: string): boolean {
  return host.startsWith("app.");
}

export function middleware(request: NextRequest) {
  const host = request.headers.get("host") ?? "";
  if (!isAppSubdomain(host)) {
    return NextResponse.next();
  }

  const pathname = request.nextUrl.pathname;

  // Sign-in is public on app subdomain (no rewrite so root /sign-in is served)
  if (pathname === "/sign-in" || pathname.startsWith("/sign-in/")) {
    return NextResponse.next();
  }

  // Restrict app subdomain: require auth cookie, else redirect to sign-in
  const hasAuth = request.cookies.get(AUTH_COOKIE_NAME)?.value;
  if (!hasAuth) {
    const signInUrl = request.nextUrl.clone();
    signInUrl.pathname = "/sign-in";
    return NextResponse.redirect(signInUrl);
  }

  // Already under /app → no rewrite
  if (pathname.startsWith("/app")) {
    return NextResponse.next();
  }
  // /analyse stays as-is so app subdomain serves the same analyse page at app..../analyse
  if (pathname === "/analyse" || pathname.startsWith("/analyse/")) {
    return NextResponse.next();
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
