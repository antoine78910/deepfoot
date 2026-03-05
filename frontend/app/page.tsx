"use client";

import { useEffect } from "react";
import Link from "next/link";
import { BGPattern } from "@/components/BGPattern";
import { LandingMatchSearch } from "@/components/LandingMatchSearch";
import { LogoCloud } from "@/components/ui/logo-cloud";
import { APP_HREF, SIGN_IN_HREF, ANALYSE_HREF, getAppAuthCallbackUrl } from "@/lib/app-url";

export default function LandingPage() {
  // If Supabase redirected here with tokens in hash (e.g. Site URL = localhost), send user to app callback
  useEffect(() => {
    const { hostname, hash } = window.location;
    if ((hostname === "localhost" || hostname === "127.0.0.1") && hash && hash.includes("access_token=")) {
      const appCallback = getAppAuthCallbackUrl();
      window.location.replace(`${appCallback}${hash}`);
    }
  }, []);

  return (
    <div className="min-h-screen bg-app-gradient text-zinc-200 flex flex-col relative overflow-hidden">
      {/* Grid background — behind gradient orbs, subtle teal tint */}
      <BGPattern variant="grid" mask="fade-edges" size={24} fill="rgba(0,255,232,0.07)" className="fixed inset-0" />
      {/* Background glow orbs (main color gradient) */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden>
        <div className="absolute -top-40 -left-40 w-80 h-80 rounded-full bg-[#00ffe8]/15 blur-[100px]" />
        <div className="absolute top-1/3 -right-32 w-96 h-96 rounded-full bg-[#00ffe8]/10 blur-[120px]" />
        <div className="absolute bottom-1/4 -left-24 w-72 h-72 rounded-full bg-[#00ffe8]/12 blur-[90px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[400px] rounded-full bg-[#00ffe8]/5 blur-[150px]" />
      </div>

      <header className="fixed top-0 left-0 right-0 z-20 w-full flex items-center justify-between px-4 sm:px-6 py-3 border-b border-white/10 bg-[#0a0a0e]/60 backdrop-blur-md">
        <Link href="/" className="flex items-center gap-2">
          <img src="/logo.png" alt="DEEPFOOT" className="h-12 sm:h-14 w-auto object-contain" />
        </Link>
        <nav className="flex items-center gap-3 sm:gap-4">
          <Link
            href={SIGN_IN_HREF}
            className="text-sm font-medium text-zinc-300 hover:text-white transition"
          >
            Log in
          </Link>
          <Link
            href={ANALYSE_HREF}
            className="text-sm font-semibold px-4 py-2 rounded-lg bg-[#00ffe8] text-black hover:opacity-90 transition"
          >
            Sign up
          </Link>
        </nav>
      </header>

      <main className="relative z-10 flex-1 flex flex-col items-center px-4 pt-24 pb-12 sm:pt-28 sm:pb-16">
        <section className="text-center max-w-3xl mx-auto mb-10 sm:mb-14">
          <h1 className="text-xl sm:text-2xl md:text-4xl lg:text-5xl font-bold text-white leading-tight mb-4 sm:whitespace-nowrap">
            Predicts all football matches <span className="text-[#00ffe8]">with AI!</span>
          </h1>
          <p className="text-zinc-400 text-lg sm:text-xl mb-8">
            Enter a team to see its upcoming matches, then get an AI-powered analysis in seconds.
          </p>
          <LandingMatchSearch analyseHref={ANALYSE_HREF} />
        </section>

        <section className="relative mx-auto mt-12 sm:mt-16 w-full max-w-6xl px-4">
          <h2 className="mb-5 text-center font-medium text-xl tracking-tight md:text-3xl">
            <span className="text-zinc-500">Trusted by experts.</span>
            <br />
            <span className="font-semibold text-white">Used by the leaders.</span>
          </h2>
          <div className="mx-auto my-5 h-px max-w-sm bg-gradient-to-r from-transparent via-white/20 to-transparent" />
          <LogoCloud />
          <div className="mt-5 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
        </section>

        {/* Banner: Based on millions of data points */}
        <section className="w-full max-w-4xl mx-auto mt-16 sm:mt-20 px-4">
          <div className="rounded-2xl bg-white/5 border border-white/10 p-6 sm:p-8 text-center">
            <p className="font-bold text-sm sm:text-base uppercase tracking-wider mb-1">
              <span className="text-white">Based on </span>
              <span className="text-[#00ffe8]">millions of data points</span>
            </p>
            <p className="text-white font-bold text-sm sm:text-base uppercase tracking-wider mb-4">
              Linked to football news
            </p>
            <p className="text-zinc-300 text-sm sm:text-base max-w-2xl mx-auto">
              Our AI is trained and connected to the same data providers as football TV channels, giving it the best analyses.
            </p>
          </div>
        </section>

        {/* Demo analysis card - same style as real analysis */}
        <section className="w-full max-w-4xl mx-auto mt-12 sm:mt-16 px-4">
          <div className="rounded-2xl bg-[#14141c] border border-white/10 p-6 shadow-lg">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="min-w-0 flex-1">
                <p className="text-zinc-500 text-sm">Analyzed match</p>
                <h2 className="text-xl md:text-2xl font-bold text-white mt-0.5">
                  Paris Saint Germain vs Real Madrid
                </h2>
              </div>
              <div className="rounded-lg bg-[#00ffe8] px-4 py-2.5 text-center flex-shrink-0">
                <p className="text-black font-semibold text-sm">AI analysis ready</p>
                <p className="text-black/80 text-xs mt-0.5">Based on stats + football news</p>
              </div>
            </div>

            <div className="border-t border-white/10 mt-5 pt-5" />

            <div className="grid md:grid-cols-2 gap-6 md:gap-8">
              <div>
                <h3 className="text-white font-semibold text-sm mb-3">Team statistics</h3>
                <div className="space-y-3">
                  <div className="rounded-xl bg-[#1c1c28] border border-white/5 p-4">
                    <p className="font-semibold text-white text-sm">Paris Saint Germain</p>
                    <p className="text-zinc-400 text-xs mt-1.5 flex items-center gap-1">
                      Form: <span className="inline-flex gap-0.5">✅ ✅ ✅ ➖ ❌</span>
                    </p>
                    <p className="text-zinc-400 text-xs mt-0.5">Goals/match: 2.1</p>
                  </div>
                  <div className="rounded-xl bg-[#1c1c28] border border-white/5 p-4">
                    <p className="font-semibold text-white text-sm">Real Madrid</p>
                    <p className="text-zinc-400 text-xs mt-1.5 flex items-center gap-1">
                      Form: <span className="inline-flex gap-0.5">✅ ✅ ➖ ➖ ❌</span>
                    </p>
                    <p className="text-zinc-400 text-xs mt-0.5">Goals/match: 2.4</p>
                  </div>
                </div>
              </div>
              <div>
                <h3 className="text-white font-semibold text-sm mb-3">AI probabilities</h3>
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="text-zinc-300 text-sm w-20 flex-shrink-0">PSG win</span>
                    <div className="flex-1 h-3 bg-[#1c1c28] rounded-full overflow-hidden min-w-0">
                      <div className="h-full bg-[#00ffe8] rounded-full" style={{ width: "44%" }} />
                    </div>
                    <span className="text-white font-semibold text-sm w-8 text-right">44%</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-zinc-300 text-sm w-20 flex-shrink-0">Draw</span>
                    <div className="flex-1 h-3 bg-[#1c1c28] rounded-full overflow-hidden min-w-0">
                      <div className="h-full bg-[#00ffe8] rounded-full" style={{ width: "26%" }} />
                    </div>
                    <span className="text-white font-semibold text-sm w-8 text-right">26%</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-zinc-300 text-sm w-20 flex-shrink-0">Real win</span>
                    <div className="flex-1 h-3 bg-[#1c1c28] rounded-full overflow-hidden min-w-0">
                      <div className="h-full bg-[#00ffe8] rounded-full" style={{ width: "30%" }} />
                    </div>
                    <span className="text-white font-semibold text-sm w-8 text-right">30%</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="border-t border-white/10 mt-6 pt-6" />

            <h3 className="text-white font-semibold text-sm mb-3">Key factors identified by AI</h3>
            <div className="grid sm:grid-cols-2 gap-4">
              <ul className="space-y-1.5 text-sm text-zinc-300">
                <li className="flex items-start gap-2">
                  <span className="text-[#00ffe8] mt-0.5">•</span>
                  <span>High offensive form</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-[#00ffe8] mt-0.5">•</span>
                  <span>Can leave spaces behind</span>
                </li>
              </ul>
              <ul className="space-y-1.5 text-sm text-zinc-300">
                <li className="flex items-start gap-2">
                  <span className="text-[#ef4444] mt-0.5">•</span>
                  <span>Dangerous fast transitions</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-[#ef4444] mt-0.5">•</span>
                  <span>Strong at home</span>
                </li>
              </ul>
            </div>

            <div className="border-t border-white/10 mt-6 pt-6" />

            <h3 className="text-white font-semibold text-sm mb-2">Quick summary</h3>
            <p className="text-zinc-300 text-sm leading-relaxed">
              Visifoot AI analyzes form, recent actions and key stats: PSG arrives with a confident attack, while Real is chaining good results. A match that promises to be open with opportunities on both sides.
            </p>

            <div className="border-t border-white/10 mt-6 pt-6" />

            <div className="relative rounded-xl border border-[#00ffe8]/40 bg-[#00ffe8]/5 p-6 shadow-[0_0_30px_rgba(0,255,232,0.2)]">
              <h3 className="text-white font-bold text-center mb-1">Advanced insights available</h3>
              <p className="text-zinc-400 text-sm text-center mb-4 max-w-md mx-auto">
                Unlock the full analysis to see all advanced insights generated by the AI for this match.
              </p>
              <div className="flex justify-center">
                <Link
                  href={ANALYSE_HREF}
                  className="inline-flex items-center justify-center px-6 py-3 rounded-xl font-semibold text-black bg-[#00ffe8] hover:opacity-90 transition"
                >
                  See all AI insights
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Feature cards */}
        <section className="w-full max-w-4xl mx-auto mt-12 sm:mt-16 px-4">
          <h2 className="text-2xl sm:text-3xl font-bold text-white text-center mb-10">
            Why use DeepFoot?
          </h2>
          <div className="grid sm:grid-cols-3 gap-6 sm:gap-8">
            <div className="rounded-2xl bg-white/5 border border-white/10 p-6 text-center shadow-lg">
              <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center mx-auto mb-4">
                <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="6" y1="20" x2="6" y2="14" stroke="#22c55e" />
                  <line x1="10" y1="20" x2="10" y2="8" stroke="#ec4899" />
                  <line x1="14" y1="20" x2="14" y2="12" stroke="#3b82f6" />
                  <line x1="18" y1="20" x2="18" y2="10" stroke="#00ffe8" />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-white mb-2">Real-time stats</h3>
              <p className="text-zinc-400 text-sm">
                Analysis of 50+ variables per match
              </p>
            </div>
            <div className="rounded-2xl bg-white/5 border border-white/10 p-6 text-center shadow-lg">
              <div className="w-12 h-12 rounded-full bg-white/10 flex items-center justify-center mx-auto mb-4">
                <svg className="w-7 h-7" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" stroke="#ef4444" />
                  <circle cx="12" cy="12" r="6" stroke="#e4e4e7" />
                  <circle cx="12" cy="12" r="2" fill="#3b82f6" stroke="#3b82f6" />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-white mb-2">Accurate predictions</h3>
              <p className="text-zinc-400 text-sm">
                AI trained on thousands of matches
              </p>
            </div>
            <div className="rounded-2xl bg-white/5 border border-white/10 p-6 text-center shadow-lg">
              <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center mx-auto mb-4">
                <svg className="w-7 h-7 text-amber-400" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-white mb-2">Instant analysis</h3>
              <p className="text-zinc-400 text-sm">
                Results in seconds
              </p>
            </div>
          </div>
        </section>

        <section className="w-full max-w-2xl mx-auto mt-16 sm:mt-24 text-center px-4">
          <p className="text-zinc-500 text-sm mb-6">
            Ready to analyze your next match?
          </p>
          <Link
            href={ANALYSE_HREF}
            className="inline-flex items-center justify-center px-6 py-3 rounded-xl font-semibold text-black bg-gradient-to-r from-[#00ffe8] to-[#00ddcc] hover:opacity-90 transition"
          >
            Open match analyzer →
          </Link>
        </section>
      </main>

      <footer className="relative z-10 py-6 text-center">
        <p className="text-zinc-500 text-xs sm:text-sm">
          Got a question? Contact us at{" "}
          <a href="mailto:app@deepfoot.io" className="text-zinc-400 hover:text-[#00ffe8] transition">
            app@deepfoot.io
          </a>
        </p>
      </footer>
    </div>
  );
}
