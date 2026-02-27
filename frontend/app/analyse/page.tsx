"use client";

import { useState, useEffect } from "react";
import { SignupModal } from "@/components/SignupModal";
import Link from "next/link";
import { AUTH_STORAGE_KEY } from "@/lib/auth";
import { getAppHref } from "@/lib/app-url";

export default function AnalysePage() {
  const [showSignupModal, setShowSignupModal] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    const stored = typeof window !== "undefined" ? localStorage.getItem(AUTH_STORAGE_KEY) : null;
    const loggedIn = stored === "1";
    setIsLoggedIn(loggedIn);
    if (!loggedIn) setShowSignupModal(true);
  }, []);

  const handleCloseModal = () => setShowSignupModal(false);
  const handleSignIn = () => {
    setShowSignupModal(false);
    if (typeof window !== "undefined") localStorage.setItem(AUTH_STORAGE_KEY, "1");
    setIsLoggedIn(true);
  };

  if (isLoggedIn) {
    const matchesHref = getAppHref("/matches");
    return (
      <main className="min-h-screen bg-app-gradient flex flex-col items-center justify-center px-4 py-12">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-white mb-2">You&apos;re signed in</h1>
          <p className="text-zinc-400 text-lg mb-6">Go to the app to analyze a match</p>
          <Link
            href={matchesHref}
            className="inline-flex px-6 py-3 rounded-xl font-semibold text-black bg-gradient-to-r from-[#00ffe8] to-[#00ddcc] hover:opacity-90 transition"
          >
            Open matches →
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-app-gradient flex flex-col items-center justify-center px-4 py-12">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-white mb-2">Match analysis</h1>
        <p className="text-zinc-400 text-lg mb-4">Create your account to analyze matches with AI</p>
        <p className="text-[#00ffe8] text-xs sm:text-sm max-w-2xl mx-auto mb-8">
          Our AI is connected to football news and crosses millions of data points for each prediction.
        </p>
        <button
          type="button"
          onClick={() => setShowSignupModal(true)}
          className="inline-flex px-6 py-3 rounded-xl font-semibold text-black bg-gradient-to-r from-[#00ffe8] to-[#00ddcc] hover:opacity-90 transition"
        >
          Sign up to analyze
        </button>
      </div>
      <SignupModal open={showSignupModal} onClose={handleCloseModal} onSignIn={handleSignIn} />
    </main>
  );
}
