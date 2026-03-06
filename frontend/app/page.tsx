"use client";

import { useEffect } from "react";
import Link from "next/link";
import { BGPattern } from "@/components/BGPattern";
import { LandingMatchSearch } from "@/components/LandingMatchSearch";
import { LogoCloud } from "@/components/ui/logo-cloud";
import { APP_HREF, SIGN_IN_HREF, SIGN_UP_HREF, ANALYSE_HREF, getAppAuthCallbackUrl } from "@/lib/app-url";

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

      <header className="fixed top-0 left-0 right-0 z-20 w-full flex items-center justify-between px-5 sm:px-8 py-3 sm:py-4 border-b border-white/10 bg-[#0a0a0e]/40 backdrop-blur-md sm:bg-[#0a0a0e]/60">
        <Link href="/" className="flex items-center gap-2">
          <img src="/logo.png" alt="DEEPFOOT" className="h-10 sm:h-12 w-auto object-contain" />
        </Link>
        <nav className="flex items-center gap-4 sm:gap-6">
          <Link
            href={SIGN_IN_HREF}
            className="text-sm font-medium text-zinc-300 hover:text-white transition"
          >
            Log in
          </Link>
          <Link
            href={SIGN_UP_HREF}
            className="text-sm font-semibold px-4 py-2 rounded-lg bg-[#00ffe8] text-black hover:opacity-90 transition"
          >
            Sign up
          </Link>
        </nav>
      </header>

      <main className="relative z-10 flex-1 flex flex-col items-center px-4 pt-24 pb-12 sm:pt-28 sm:pb-16">
        <section className="text-center max-w-3xl mx-auto mb-10 sm:mb-14 pt-4">
          <h1 className="text-3xl sm:text-4xl md:text-4xl lg:text-5xl font-bold text-white leading-tight mb-4 sm:mb-5 sm:whitespace-nowrap">
            Predicts all football matches <span className="text-[#00ffe8]">with AI!</span>
          </h1>
          <p className="text-zinc-400 text-base sm:text-lg mb-8">
            Enter a team to see its upcoming matches, then get an AI-powered analysis in seconds.
          </p>
          <LandingMatchSearch analyseHref={ANALYSE_HREF} />
        </section>

        <section className="relative mx-auto -mt-1 sm:mt-0 w-full max-w-6xl px-4 flex-shrink-0">
          <h2 className="mb-2 text-center text-sm font-medium tracking-wide text-zinc-500 sm:text-base">
            27 Major European Football Leagues Covered
          </h2>
          <div className="mx-auto my-2 h-px max-w-xs bg-gradient-to-r from-transparent via-white/20 to-transparent" />
          <LogoCloud />
          <div className="mt-2 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
        </section>

        {/* Banner: Based on millions of data points */}
        <section className="w-full max-w-4xl mx-auto mt-16 sm:mt-20 px-4">
          <div className="rounded-2xl bg-white/5 border border-white/10 p-6 sm:p-8 text-center">
            <p className="font-bold text-sm sm:text-base uppercase tracking-wider mb-1">
              <span className="text-white">Based on </span>
              <Link href={ANALYSE_HREF} className="text-[#00ffe8] hover:opacity-90 transition">
                millions of data points
              </Link>
            </p>
            <p className="text-white font-bold text-sm sm:text-base uppercase tracking-wider mb-4">
              Linked to football news
            </p>
            <p className="text-zinc-300 text-sm sm:text-base max-w-2xl mx-auto">
              Our AI is trained and connected to the same data providers as football TV channels, giving it the best analyses.
            </p>
          </div>
        </section>

        {/* Demo analysis card — vraie analyse DeepFoot style (PSG vs Chelsea) */}
        <section className="w-full max-w-4xl mx-auto mt-12 sm:mt-16 px-4">
          <div className="rounded-2xl bg-[#14141c] border border-white/10 p-6 shadow-lg">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="min-w-0 flex-1 flex items-center gap-3">
                <img src="https://media.api-sports.io/football/teams/85.png" alt="" className="w-12 h-12 object-contain flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-zinc-500 text-sm">Analyzed match</p>
                  <h2 className="text-xl md:text-2xl font-bold text-white mt-0.5">
                    Paris Saint-Germain vs Chelsea
                  </h2>
                </div>
                <img src="https://media.api-sports.io/football/teams/49.png" alt="" className="w-12 h-12 object-contain flex-shrink-0" />
              </div>
              <div className="rounded-lg bg-[#00ffe8] px-4 py-2.5 text-center flex-shrink-0">
                <p className="text-black font-semibold text-sm">AI analysis ready</p>
                <p className="text-black/80 text-xs mt-0.5">Based on stats + football news</p>
              </div>
            </div>

            <div className="border-t border-white/10 mt-5 pt-5" />

            <h3 className="text-white font-semibold text-sm mb-3">Team statistics</h3>
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="rounded-xl bg-[#1c1c28] border border-white/5 p-4 flex items-center gap-3">
                <img src="https://media.api-sports.io/football/teams/85.png" alt="" className="w-10 h-10 object-contain flex-shrink-0" />
                <div className="min-w-0">
                  <p className="font-semibold text-white text-sm">Paris Saint-Germain</p>
                  <p className="text-zinc-400 text-xs mt-1 flex items-center gap-1">
                    Form: <span className="inline-flex gap-0.5">✅ ✅ ➖ ❌ ✅</span> <span className="text-zinc-500">W-D-L: 3-1-1</span>
                  </p>
                  <p className="text-zinc-400 text-xs mt-0.5">Goals/match: 2.2 · xG: 2.1</p>
                </div>
              </div>
              <div className="rounded-xl bg-[#1c1c28] border border-white/5 p-4 flex items-center gap-3">
                <img src="https://media.api-sports.io/football/teams/49.png" alt="" className="w-10 h-10 object-contain flex-shrink-0" />
                <div className="min-w-0">
                  <p className="font-semibold text-white text-sm">Chelsea</p>
                  <p className="text-zinc-400 text-xs mt-1 flex items-center gap-1">
                    Form: <span className="inline-flex gap-0.5">✅ ➖ ✅ ✅ ➖</span> <span className="text-zinc-500">W-D-L: 3-2-0</span>
                  </p>
                  <p className="text-zinc-400 text-xs mt-0.5">Goals/match: 1.8 · xG: 1.9</p>
                </div>
              </div>
            </div>

            <div className="border-t border-white/10 mt-5 pt-5" />

            <h3 className="text-white font-semibold text-sm mb-3">AI probabilities</h3>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-zinc-300 text-sm w-24 flex-shrink-0">PSG win</span>
                <div className="flex-1 h-3 bg-[#1c1c28] rounded-full overflow-hidden min-w-0">
                  <div className="h-full bg-[#00ffe8] rounded-full" style={{ width: "42%" }} />
                </div>
                <span className="text-white font-semibold text-sm w-8 text-right">42%</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-zinc-300 text-sm w-24 flex-shrink-0">Draw</span>
                <div className="flex-1 h-3 bg-[#1c1c28] rounded-full overflow-hidden min-w-0">
                  <div className="h-full bg-zinc-400 rounded-full" style={{ width: "28%" }} />
                </div>
                <span className="text-white font-semibold text-sm w-8 text-right">28%</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-zinc-300 text-sm w-24 flex-shrink-0">Chelsea win</span>
                <div className="flex-1 h-3 bg-[#1c1c28] rounded-full overflow-hidden min-w-0">
                  <div className="h-full bg-[#ef4444]/80 rounded-full" style={{ width: "30%" }} />
                </div>
                <span className="text-white font-semibold text-sm w-8 text-right">30%</span>
              </div>
            </div>

            <div className="border-t border-white/10 mt-6 pt-6" />

            <h3 className="text-white font-semibold text-sm mb-3">Key factors by AI</h3>
            <div className="grid sm:grid-cols-2 gap-4">
              <ul className="space-y-1.5 text-sm text-zinc-300">
                <li className="flex items-start gap-2">
                  <span className="text-[#00ffe8] mt-0.5">•</span>
                  <span>PSG strong at home, high xG in last 5</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-[#00ffe8] mt-0.5">•</span>
                  <span>Defensive line can leave space in transition</span>
                </li>
              </ul>
              <ul className="space-y-1.5 text-sm text-zinc-300">
                <li className="flex items-start gap-2">
                  <span className="text-[#ef4444] mt-0.5">•</span>
                  <span>Chelsea unbeaten in last 5, solid form</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-[#ef4444] mt-0.5">•</span>
                  <span>Counter-attack threat, set-pieces danger</span>
                </li>
              </ul>
            </div>

            <div className="border-t border-white/10 mt-6 pt-6" />

            <h3 className="text-white font-semibold text-sm mb-2">Quick summary</h3>
            <p className="text-zinc-300 text-sm leading-relaxed">
              DeepFoot AI combines form, xG and H2H: PSG has the edge at home with a higher attacking output, but Chelsea are on an unbeaten run and dangerous on the break. The model gives a slight advantage to the hosts (42% vs 30% away win), with a 28% draw. Key battle: PSG’s possession vs Chelsea’s transitions.
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

        {/* Why use DeepFoot — 3 feature blocks */}
        <section className="w-full max-w-5xl mx-auto mt-14 sm:mt-20 px-4 sm:px-6">
          <h2 className="text-2xl sm:text-3xl font-bold text-white text-center mb-10 sm:mb-12">
            Why use DeepFoot?
          </h2>
          <div className="grid gap-6 sm:gap-8 md:grid-cols-3">
            {/* AI Match Predictions */}
            <div className="group rounded-2xl bg-white/[0.06] border border-white/10 p-6 sm:p-7 shadow-lg hover:border-[#00ffe8]/30 hover:shadow-[0_0_40px_rgba(0,255,232,0.08)] transition-all duration-300">
              <div className="text-3xl sm:text-4xl mb-4">🧠</div>
              <h3 className="text-lg sm:text-xl font-bold text-white mb-2">AI Match Predictions</h3>
              <p className="text-zinc-400 text-sm sm:text-base mb-4 leading-relaxed">
                Automatic analysis of thousands of matches to compute real probabilities.
              </p>
              <ul className="space-y-1.5 text-zinc-300 text-sm mb-4">
                <li>• win / draw / loss probabilities</li>
                <li>• over / under probabilities</li>
                <li>• BTTS probability</li>
                <li>• upset probability</li>
              </ul>
              <Link
                href={ANALYSE_HREF}
                className="inline-block text-[#00ffe8] text-sm font-medium hover:opacity-90 transition"
              >
                👉 Find value bets before the bookmakers.
              </Link>
            </div>

            {/* Advanced Match Analytics */}
            <div className="group rounded-2xl bg-white/[0.06] border border-white/10 p-6 sm:p-7 shadow-lg hover:border-[#00ffe8]/30 hover:shadow-[0_0_40px_rgba(0,255,232,0.08)] transition-all duration-300">
              <div className="text-3xl sm:text-4xl mb-4">📊</div>
              <h3 className="text-lg sm:text-xl font-bold text-white mb-2">Advanced Match Analytics</h3>
              <p className="text-zinc-400 text-sm sm:text-base mb-4 leading-relaxed">
                All key data in one single analysis:
              </p>
              <ul className="space-y-1.5 text-zinc-300 text-sm mb-4">
                <li>• team form</li>
                <li>• head-to-head history</li>
                <li>• standings</li>
                <li>• recent performance</li>
                <li>• match trends</li>
              </ul>
              <Link
                href={ANALYSE_HREF}
                className="inline-block text-[#00ffe8] text-sm font-medium hover:opacity-90 transition"
              >
                👉 Understand why a team is the favourite.
              </Link>
            </div>

            {/* Smart Betting Insights */}
            <div className="group rounded-2xl bg-white/[0.06] border border-white/10 p-6 sm:p-7 shadow-lg hover:border-[#00ffe8]/30 hover:shadow-[0_0_40px_rgba(0,255,232,0.08)] transition-all duration-300">
              <div className="text-3xl sm:text-4xl mb-4">📈</div>
              <h3 className="text-lg sm:text-xl font-bold text-white mb-2">Smart Betting Insights</h3>
              <p className="text-zinc-400 text-sm sm:text-base mb-4 leading-relaxed">
                DeepFoot turns data into betting decisions.
              </p>
              <ul className="space-y-1.5 text-zinc-300 text-sm mb-4">
                <li>• double chance probabilities</li>
                <li>• over/under insights</li>
                <li>• market probabilities</li>
                <li>• upset detection</li>
              </ul>
              <Link
                href={ANALYSE_HREF}
                className="inline-block text-[#00ffe8] text-sm font-medium hover:opacity-90 transition"
              >
                👉 Identify the safest and most profitable bets.
              </Link>
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
