"use client";

import { useState } from "react";
import Link from "next/link";
import { SIGN_IN_HREF } from "@/lib/app-url";

interface SignupModalProps {
  open: boolean;
  onClose: () => void;
  onSignIn?: () => void;
}

export function SignupModal({ open, onClose, onSignIn }: SignupModalProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const canSubmit = email.trim().length > 0 && password.trim().length >= 6;

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70" onClick={onClose}>
      <div
        className="bg-[#050816] border border-white/15 rounded-2xl p-8 max-w-md w-full shadow-2xl"
        style={{ opacity: 1, transform: "none" }}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-white text-2xl font-bold mb-2 text-center">Create account</h2>
        <p className="text-white/60 text-center mb-6 text-sm">Sign up for free to unlock the full analysis</p>

        <div className="space-y-3">
          <button
            type="button"
            className="w-full h-14 px-6 bg-white hover:bg-gray-100 text-gray-800 font-semibold rounded-lg transition-all duration-200 flex items-center justify-center gap-3 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
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

          <div className="space-y-3">
            <input
              placeholder="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-transparent"
            />
            <input
              placeholder="Password (min. 6 characters)"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-teal-400 focus:border-transparent"
            />
            <button
              type="button"
              disabled={!canSubmit}
              className="w-full h-12 px-6 bg-gradient-to-r from-teal-400 to-emerald-400 hover:from-teal-500 hover:to-emerald-500 text-black font-semibold rounded-lg transition-all duration-200 flex items-center justify-center gap-2 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect width="20" height="16" x="2" y="4" rx="2" />
                <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
              </svg>
              <span>Sign up</span>
            </button>
          </div>
        </div>

        <div className="text-center mt-4">
          <Link href={SIGN_IN_HREF} className="text-teal-400 hover:text-teal-300 text-sm underline" onClick={onClose}>
            Already have an account? Sign in
          </Link>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="text-white/60 text-sm mt-6 hover:text-white transition-colors w-full text-center py-2 hover:bg-white/5 rounded-lg"
        >
          Close
        </button>
      </div>
    </div>
  );
}
