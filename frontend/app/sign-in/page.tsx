"use client";

import { useState } from "react";
import Link from "next/link";
import {
  setAuthCookie,
  setUserInStorage,
  displayNameFromEmail,
  type UserInfo,
} from "@/lib/auth";
import { getAppHref } from "@/lib/app-url";

export default function SignInPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const canSubmit = email.trim().length > 0 && password.trim().length >= 6;

  const handleSignIn = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    const user: UserInfo = {
      displayName: displayNameFromEmail(email.trim()),
      email: email.trim(),
      plan: "free",
    };
    setAuthCookie();
    setUserInStorage(user);
    // Redirect to app root: on app subdomain go to /, else app URL (subdomain or /app)
    const isApp = typeof window !== "undefined" && window.location.hostname.startsWith("app.");
    const target = isApp ? `${window.location.origin}/` : getAppHref("/");
    window.location.href = target;
  };

  return (
    <div className="min-h-screen bg-app-gradient flex flex-col items-center justify-center px-4 py-12">
      <div className="bg-[#050816] border border-white/15 rounded-2xl p-8 max-w-md w-full shadow-2xl">
        <h1 className="text-white text-2xl font-bold mb-2 text-center">Sign in</h1>
        <p className="text-white/60 text-center mb-6 text-sm">Sign in to your account to analyze matches</p>

        <form onSubmit={handleSignIn} className="space-y-3">
          <button
            type="button"
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

          <input
            placeholder="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-transparent"
          />
          <input
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-transparent"
          />
          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full h-12 px-6 bg-gradient-to-r from-teal-400 to-emerald-400 hover:from-teal-500 hover:to-emerald-500 text-black font-semibold rounded-lg transition-all duration-200 flex items-center justify-center gap-2 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Sign in
          </button>
        </form>

        <p className="text-center mt-4">
          <Link href="/" className="text-teal-400 hover:text-teal-300 text-sm underline">
            Don&apos;t have an account? Sign up
          </Link>
        </p>

        <Link
          href="/"
          className="text-white/60 text-sm mt-6 hover:text-white transition-colors w-full text-center py-2 hover:bg-white/5 rounded-lg block"
        >
          Back to home
        </Link>
      </div>
    </div>
  );
}
