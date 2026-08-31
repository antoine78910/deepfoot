"use client";

import { useEffect } from "react";
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

export function ClientProviders({ children }: { children: React.ReactNode }) {
  return (
    <LanguageProvider>
      <OAuthCodeCatcher />
      {children}
    </LanguageProvider>
  );
}
