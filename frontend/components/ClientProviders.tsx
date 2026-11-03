"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { LanguageProvider } from "@/contexts/LanguageContext";

/** If Supabase sent the PKCE `code` to the wrong path (Site URL), finish login on /auth/callback. */
function OAuthCodeCatcher() {
  useEffect(() => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    if (!url.searchParams.get("code")) return;
    if (url.pathname === "/auth/callback" || url.pathname.startsWith("/auth/callback/")) return;
    window.location.replace(`/auth/callback${url.search}${url.hash}`);
  }, []);
  return null;
}

/** Extra page views on App Router client navigations. First load is already fired by the pixel snippet. */
function WhopPixelRouteTracker() {
  const pathname = usePathname();
  const isFirstLoad = useRef(true);
  useEffect(() => {
    if (isFirstLoad.current) {
      isFirstLoad.current = false;
      return;
    }
    const whop = (window as unknown as { whop?: { track?: (...args: unknown[]) => void } }).whop;
    if (typeof whop?.track === "function") {
      whop.track("page");
    }
  }, [pathname]);
  return null;
}

export function ClientProviders({ children }: { children: React.ReactNode }) {
  return (
    <LanguageProvider>
      <OAuthCodeCatcher />
      <WhopPixelRouteTracker />
      {children}
    </LanguageProvider>
  );
}
