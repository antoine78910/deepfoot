"use client";

import { Suspense, useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  setAuthCookie,
  setUserInStorage,
  displayNameFromEmail,
  type UserInfo,
} from "@/lib/auth";
import { SIGN_IN_HREF, ANALYSE_HREF, getAppAuthCallbackUrl, getAppRootUrl } from "@/lib/app-url";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

function SignUpPageContent() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [emailSent, setEmailSent] = useState(false);
  const searchParams = useSearchParams();
  const next = searchParams.get("next");

  // If Supabase redirected here with tokens in hash (wrong Site URL in dashboard), redirect to /auth/callback on same host
  useEffect(() => {
    if (typeof window === "undefined") return;
    const { hash, hostname } = window.location;
    if (hash && hash.includes("access_token=")) {
      const callbackPath = "/auth/callback";
      const target = hostname.startsWith("app.")
        ? `${window.location.origin}${callbackPath}${hash.startsWith("#") ? hash : `#${hash}`}`
        : `${getAppAuthCallbackUrl()}${hash.startsWith("#") ? hash : `#${hash}`}`;
      window.location.replace(target);
    }
  }, []);

  const canSubmit = email.trim().length > 0 && password.trim().length >= 6;

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit || loading) return;
    setError(null);
    setLoading(true);
    try {
      const supabase = getSupabaseBrowserClient();
      const { data, error: err } = await supabase.auth.signUp({
        email: email.trim(),
        password,
        options: {
          emailRedirectTo: getAppAuthCallbackUrl(),
        },
      });
      if (err) {
        setError(err.message);
        setLoading(false);
        return;
      }
      if (data?.user && !data?.session) {
        setLoading(false);
        setEmailSent(true);
      } else if (data?.session && data?.user) {
        const user: UserInfo = {
          id: data.user.id,
          displayName: displayNameFromEmail(data.user.email ?? email.trim()),
          email: (data.user.email ?? email.trim()) || "",
          plan: "free",
        };
        setAuthCookie();
        setUserInStorage(user);
        const isApp = typeof window !== "undefined" && window.location.hostname.startsWith("app.");
        const safeNext = next && next.startsWith("/") ? next : null;
        const target = safeNext
          ? `${window.location.origin}${safeNext}`
          : isApp
            ? `${window.location.origin}/`
            : getAppRootUrl();
        window.location.href = target;
        return;
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Sign up failed");
    }
    setLoading(false);
  };

  const handleGoogle = async () => {
    try {
      const supabase = getSupabaseBrowserClient();
      const safeNext = next && next.startsWith("/") ? next : null;
      const redirectTo = safeNext
        ? `${getAppAuthCallbackUrl()}?next=${encodeURIComponent(safeNext)}`
        : getAppAuthCallbackUrl();
      await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo,
        },
      });
    } catch (e: any) {
      alert(e?.message || "Google sign-up is not configured.");
    }
  };

  return (
    <div className="min-h-screen bg-app-gradient flex flex-col items-center px-4 pt-24 pb-12 relative overflow-hidden">
      <header className="fixed top-0 left-0 right-0 z-20 w-full flex items-center px-5 sm:px-8 py-3 sm:py-4 bg-transparent">
        <Link href="/" className="flex items-center gap-2">
          <img src="/logo.png" alt="DEEPFOOT" className="h-10 sm:h-12 w-auto object-contain" />
        </Link>
      </header>
      <div className="pointer-events-none absolute inset-0" aria-hidden>
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full bg-[#00ffe8]/18 blur-[120px]" />
        <div className="absolute top-1/3 -right-32 w-[520px] h-[520px] rounded-full bg-emerald-400/12 blur-[140px]" />
        <div className="absolute -bottom-48 left-1/3 w-[520px] h-[520px] rounded-full bg-sky-400/10 blur-[150px]" />
      </div>

      <div className="relative w-full max-w-md isolate flex-1 flex flex-col items-center justify-center">
        <div className="pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-r from-[#00ffe8]/35 via-transparent to-emerald-400/30 blur-xl opacity-90" aria-hidden />
        <div className="relative rounded-2xl p-[1px] bg-gradient-to-r from-[#00ffe8]/70 via-white/10 to-emerald-400/60">
          <div className="bg-[#050816]/95 backdrop-blur rounded-2xl p-8 w-full shadow-2xl relative z-10">
            <h1 className="text-white text-2xl font-bold mb-2 text-center">Sign up</h1>
            <p className="text-white/60 text-center mb-6 text-sm">Create an account to analyze matches with AI</p>

            {emailSent ? (
              <div className="rounded-xl bg-emerald-500/15 border border-emerald-400/40 p-4 text-center">
                <p className="text-white font-medium mb-1">Check your email</p>
                <p className="text-white/70 text-sm">
                  We sent a confirmation link to <span className="text-[#00ffe8] font-medium">{email}</span>. Click it to validate your account, then sign in.
                </p>
                <Link
                  href={SIGN_IN_HREF}
                  className="mt-4 inline-block text-teal-400 hover:text-teal-300 text-sm underline"
                >
                  Go to sign in
                </Link>
                <button
                  type="button"
                  onClick={() => { setEmailSent(false); setEmail(""); setPassword(""); setError(null); }}
                  className="block mt-2 mx-auto text-white/60 hover:text-white text-sm"
                >
                  Use another email
                </button>
              </div>
            ) : (
            <form onSubmit={handleSignUp} className="space-y-3">
              <button
                type="button"
                onClick={handleGoogle}
                className="w-full h-14 px-6 bg-white hover:bg-gray-100 text-gray-800 font-semibold rounded-lg transition-all duration-200 flex items-center justify-center gap-3 shadow-lg hover:shadow-xl"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
                <span>Continue with Google</span>
              </button>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/20" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="px-2 bg-[#050816] text-white/60">or</span>
                </div>
              </div>

              {error && (
                <p className="text-red-400 text-sm text-center -mb-1">{error}</p>
              )}
              <input
                placeholder="Email"
                type="email"
                value={email}
                onChange={(e) => { setEmail(e.target.value); setError(null); }}
                className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-transparent"
                autoComplete="email"
              />
              <input
                placeholder="Password (min 6 characters)"
                type="password"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setError(null); }}
                className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-transparent"
                autoComplete="new-password"
              />
              <button
                type="submit"
                disabled={!canSubmit || loading}
                className="w-full h-12 px-6 bg-gradient-to-r from-teal-400 to-emerald-400 hover:from-teal-500 hover:to-emerald-500 text-black font-semibold rounded-lg transition-all duration-200 flex items-center justify-center gap-2 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="inline-block w-5 h-5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                ) : (
                  "Create account"
                )}
              </button>
            </form>
            )}

            <p className="text-center mt-4">
              <Link href={SIGN_IN_HREF} className="text-teal-400 hover:text-teal-300 text-sm underline">
                Already have an account? Sign in
              </Link>
            </p>

            <Link
              href={ANALYSE_HREF}
              className="text-white/60 text-sm mt-6 hover:text-white transition-colors w-full text-center py-2 hover:bg-white/5 rounded-lg block"
            >
              Back to match analyzer
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SignUpPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-app-gradient flex items-center justify-center text-zinc-400">Loading...</div>}>
      <SignUpPageContent />
    </Suspense>
  );
}
