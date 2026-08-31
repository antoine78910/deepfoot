"use client";

import { useEffect, useState } from "react";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";
import { ensureUserProfile } from "@/lib/supabase/profile";
import {
  setAuthCookie,
  setUserInStorage,
  displayNameFromEmail,
  type UserInfo,
} from "@/lib/auth";
import { getAppHref } from "@/lib/app-url";
import { takeOAuthNext, clearGoogleOAuthLock } from "@/lib/oauth-callback";
import { trackDatafastGoal } from "@/lib/datafast";

type CallbackResult =
  | { ok: true; target: string }
  | { ok: false; error: string };

const exchangeByCode = new Map<string, Promise<CallbackResult>>();

function mapOAuthError(raw: string): string {
  const lower = raw.toLowerCase();
  if (lower.includes("flow state") || lower.includes("oauth state")) {
    return "Google sign-in expired. Close extra tabs, then try again from this same page (app.deepfoot.io).";
  }
  return raw;
}

async function completeOAuthCallback(): Promise<CallbackResult> {
  const url = new URL(window.location.href);
  const code = url.searchParams.get("code");
  const oauthError = url.searchParams.get("error_description") || url.searchParams.get("error");
  if (oauthError && !code) {
    clearGoogleOAuthLock();
    return { ok: false, error: decodeURIComponent(oauthError.replace(/\+/g, " ")) };
  }

  const href = window.location.href;
  const hasHash = href.includes("#");
  const hashParams = hasHash ? new URLSearchParams(href.split("#")[1] || "") : null;
  const accessToken = hashParams?.get("access_token");
  const refreshToken = hashParams?.get("refresh_token");
  const exchangeKey = code || (accessToken ? `hash:${accessToken.slice(0, 24)}` : "missing");

  const existing = exchangeByCode.get(exchangeKey);
  if (existing) return existing;

  const work = (async (): Promise<CallbackResult> => {
    try {
      const supabase = getSupabaseBrowserClient();

      if (accessToken && refreshToken) {
        const { error: setSessionError } = await supabase.auth.setSession({
          access_token: accessToken,
          refresh_token: refreshToken,
        });
        if (setSessionError) throw setSessionError;
      } else {
        if (!code) throw new Error("Missing OAuth code");
        const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);
        if (exchangeError) throw exchangeError;
      }

      clearGoogleOAuthLock();

      const { data: sessionData } = await supabase.auth.getSession();
      const user = sessionData?.session?.user ?? (await supabase.auth.getUser()).data.user;
      const email = user?.email ?? "";

      const displayName =
        (user?.user_metadata as { full_name?: string; name?: string } | undefined)?.full_name ||
        (user?.user_metadata as { full_name?: string; name?: string } | undefined)?.name ||
        (email ? displayNameFromEmail(email) : "User");

      const info: UserInfo = {
        id: user?.id,
        displayName,
        email: email || "unknown",
        plan: "free",
      };

      setAuthCookie();
      setUserInStorage(info);
      await ensureUserProfile(user?.id);
      trackDatafastGoal("account_verified_landing");

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
          return {
            ok: true,
            target: getAppHref(
              `/matches?home=${encodeURIComponent(parsed.home)}&away=${encodeURIComponent(parsed.away)}`
            ),
          };
        }
      } catch {
        // ignore
      }

      const nextUrl = takeOAuthNext();
      const isApp = window.location.hostname.startsWith("app.");
      const target = nextUrl
        ? (nextUrl.startsWith("http") ? nextUrl : `${window.location.origin}${nextUrl}`)
        : isApp
          ? `${window.location.origin}/`
          : getAppHref("/");
      return { ok: true, target };
    } catch (e: unknown) {
      clearGoogleOAuthLock();
      const raw = e instanceof Error ? e.message : "OAuth callback failed";
      return { ok: false, error: mapOAuthError(raw) };
    }
  })();

  exchangeByCode.set(exchangeKey, work);
  return work;
}

export default function AuthCallbackPage() {
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const result = await completeOAuthCallback();
      if (cancelled) return;
      if (!result.ok) {
        setError(result.error);
        setStatus("error");
        return;
      }
      setStatus("ok");
      window.location.replace(result.target);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

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
