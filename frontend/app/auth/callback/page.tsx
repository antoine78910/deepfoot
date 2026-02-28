"use client";

import { useEffect, useMemo, useState } from "react";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";
import {
  setAuthCookie,
  setUserInStorage,
  displayNameFromEmail,
  type UserInfo,
} from "@/lib/auth";
import { getAppHref } from "@/lib/app-url";

export default function AuthCallbackPage() {
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");

  const nextUrl = useMemo(() => {
    if (typeof window === "undefined") return null;
    const url = new URL(window.location.href);
    return url.searchParams.get("next");
  }, []);

  useEffect(() => {
    const run = async () => {
      try {
        const supabase = getSupabaseBrowserClient();
        const href = window.location.href;
        const hasHash = href.includes("#");
        const hashParams = hasHash ? new URLSearchParams(href.split("#")[1] || "") : null;
        const accessToken = hashParams?.get("access_token");
        const refreshToken = hashParams?.get("refresh_token");

        if (accessToken && refreshToken) {
          // Implicit flow: tokens in hash (e.g. Supabase redirected to Site URL with hash)
          const { data, error: setError } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });
          if (setError) throw setError;
        } else {
          // PKCE: exchange ?code=... for a session
          const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(href);
          if (exchangeError) throw exchangeError;
        }

        const { data: sessionData } = await supabase.auth.getSession();
        const user = sessionData?.session?.user ?? (await supabase.auth.getUser()).data.user;
        const email = user?.email ?? "";

        const displayName =
          (user?.user_metadata as any)?.full_name ||
          (user?.user_metadata as any)?.name ||
          (email ? displayNameFromEmail(email) : "User");

        const info: UserInfo = {
          displayName,
          email: email || "unknown",
          plan: "free",
        };

        setAuthCookie();
        setUserInStorage(info);

        setStatus("ok");

        let target: string;
        const PENDING_COOKIE = "visifoot_pending_match";
        try {
          let parsed: { home?: string; away?: string } | null = null;
          const cookieMatch = document.cookie.match(new RegExp(`(?:^|; )${PENDING_COOKIE}=([^;]*)`));
          if (cookieMatch) {
            try {
              parsed = JSON.parse(decodeURIComponent(cookieMatch[1])) as { home?: string; away?: string };
              document.cookie = `${PENDING_COOKIE}=; path=/; max-age=0; domain=.deepfoot.io`;
              document.cookie = `${PENDING_COOKIE}=; path=/; max-age=0`;
            } catch {
              // ignore
            }
          }
          if (!parsed) {
            const raw = sessionStorage.getItem("visifoot_pending_match");
            if (raw) {
              parsed = JSON.parse(raw) as { home?: string; away?: string };
              sessionStorage.removeItem("visifoot_pending_match");
            }
          }
          if (parsed?.home && parsed?.away) {
            target = getAppHref(
              `/matches?home=${encodeURIComponent(parsed.home)}&away=${encodeURIComponent(parsed.away)}`
            );
            window.location.replace(target);
            return;
          }
        } catch {
          // ignore
        }

        const isApp = window.location.hostname.startsWith("app.");
        target = nextUrl
          ? nextUrl
          : isApp
            ? `${window.location.origin}/`
            : getAppHref("/");
        window.location.replace(target);
      } catch (e: any) {
        setError(e?.message || "OAuth callback failed");
        setStatus("error");
      }
    };
    void run();
  }, [nextUrl]);

  return (
    <div className="min-h-screen bg-app-gradient flex items-center justify-center px-4 py-12">
      <div className="bg-[#050816] border border-white/15 rounded-2xl p-8 max-w-md w-full shadow-2xl text-center">
        {status === "loading" ? (
          <>
            <h1 className="text-white text-xl font-bold mb-2">Signing you in…</h1>
            <p className="text-white/60 text-sm">Completing Google authentication.</p>
          </>
        ) : status === "error" ? (
          <>
            <h1 className="text-white text-xl font-bold mb-2">Sign-in failed</h1>
            <p className="text-white/60 text-sm break-words">{error}</p>
            <a
              href="/sign-in"
              className="inline-flex mt-6 h-11 px-5 items-center justify-center rounded-lg bg-white text-gray-900 font-semibold hover:bg-gray-100"
            >
              Back to sign-in
            </a>
          </>
        ) : (
          <>
            <h1 className="text-white text-xl font-bold mb-2">Signed in</h1>
            <p className="text-white/60 text-sm">Redirecting…</p>
          </>
        )}
      </div>
    </div>
  );
}

