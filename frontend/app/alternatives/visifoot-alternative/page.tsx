import Link from "next/link";
import { buildPageMetadata } from "@/lib/seo/metadata";
import { faqPageSchema, breadcrumbSchema } from "@/lib/seo/schema";
import { SITE_URL } from "@/lib/seo/site";

export const metadata = buildPageMetadata({
  title: "Best Visifoot Alternative: AI Football Predictions",
  description:
    "Looking for a Visifoot alternative? DeepFoot offers AI football match predictions with 1X2, over/under, BTTS and scenario analysis across 27 European leagues.",
  path: "/alternatives/visifoot-alternative",
});

const FAQ = [
  {
    question: "What is the best alternative to Visifoot?",
    answer:
      "DeepFoot is a strong alternative: it provides AI-powered match predictions with explicit probabilities (1X2, over/under, BTTS), scenario analysis, and coverage of 27 major European leagues, with analyses linked to football news and stats.",
  },
  {
    question: "Is DeepFoot free to use?",
    answer:
      "You can run AI match analyses and see predictions. Premium plans unlock more analyses per month and advanced features.",
  },
  {
    question: "Does DeepFoot work like Visifoot?",
    answer:
      "Both use AI for football predictions. DeepFoot focuses on clear probability outputs and written scenario analysis. You can try it at deepfoot.ai/analyse and compare.",
  },
  {
    question: "Which leagues does DeepFoot cover?",
    answer:
      "DeepFoot covers 27 European leagues including Premier League, La Liga, Serie A, Bundesliga, Ligue 1, and Champions League. See the analyse page for the full list.",
  },
];

export default function VisifootAlternativePage() {
  const breadcrumb = breadcrumbSchema([
    { name: "Home", path: "/" },
    { name: "Alternatives", path: "/alternatives/visifoot-alternative" },
    { name: "Visifoot Alternative", path: "/alternatives/visifoot-alternative" },
  ]);
  const faqSchema = faqPageSchema(FAQ, `${SITE_URL}/alternatives/visifoot-alternative`);

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: breadcrumb }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: faqSchema }}
      />
      <div className="min-h-screen bg-app-gradient text-zinc-200">
        <header className="border-b border-white/10 bg-[#0a0a0e]/60 backdrop-blur-md">
          <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4">
            <Link href="/" className="text-[#00ffe8] hover:opacity-90">
              ← DeepFoot
            </Link>
            <Link href="/analyse" className="rounded-lg bg-[#00ffe8] px-4 py-2 text-sm font-semibold text-black hover:opacity-90">
              Try AI predictions
            </Link>
          </div>
        </header>

        <main className="mx-auto max-w-4xl px-4 py-10 sm:py-14">
          <nav className="mb-6 text-sm text-zinc-400">
            <Link href="/" className="hover:text-white">Home</Link>
            <span className="mx-2">/</span>
            <Link href="/ai-football-predictions" className="hover:text-white">AI Football Predictions</Link>
            <span className="mx-2">/</span>
            <span className="text-zinc-300">Visifoot Alternative</span>
          </nav>

          <h1 className="text-3xl font-bold text-white sm:text-4xl">
            Best Visifoot Alternative: AI Football Predictions
          </h1>
          <p className="mt-4 text-lg text-zinc-400">
            If you’re looking for an alternative to Visifoot for AI football predictions, DeepFoot offers probability-based match analysis, scenario breakdowns, and broad league coverage.
          </p>

          <section className="mt-10">
            <h2 className="text-xl font-bold text-white">What to expect from DeepFoot</h2>
            <ul className="mt-4 list-inside list-disc space-y-2 text-zinc-300">
              <li><strong className="text-white">1X2 probabilities</strong> — Win, draw, and away win percentages for every match.</li>
              <li><strong className="text-white">Over/Under</strong> — Probability that the match goes over or under a given goals line.</li>
              <li><strong className="text-white">BTTS</strong> — Both teams to score probability.</li>
              <li><strong className="text-white">Scenario analysis</strong> — Key factors and summary in plain language, linked to stats and news.</li>
              <li><strong className="text-white">27 leagues</strong> — Premier League, La Liga, Serie A, Bundesliga, Champions League, and more.</li>
            </ul>
          </section>

          <section className="mt-10">
            <h2 className="text-xl font-bold text-white">Why consider an alternative?</h2>
            <p className="mt-4 text-zinc-300">
              You might want to compare tools for different probability outputs, league coverage, or analysis depth. DeepFoot is built for users who want explicit percentages and clear, data-driven reasoning. Predictions are probabilistic—no tool can guarantee results—but you can use DeepFoot alongside other predictors to cross-check.
            </p>
          </section>

          <section className="mt-10">
            <h2 className="text-xl font-bold text-white">How to try DeepFoot</h2>
            <p className="mt-4 text-zinc-300">
              Go to{" "}
              <Link href="/analyse" className="text-[#00ffe8] hover:opacity-90">
                DeepFoot’s analyse page
              </Link>
              , enter the two teams, and get an AI analysis with probabilities and key factors in seconds. No sign-up required for a first try.
            </p>
          </section>

          <section className="mt-12">
            <h2 className="text-xl font-bold text-white">FAQ</h2>
            <ul className="mt-4 space-y-6">
              {FAQ.map((item, i) => (
                <li key={i}>
                  <h3 className="font-semibold text-white">{item.question}</h3>
                  <p className="mt-2 text-zinc-400">{item.answer}</p>
                </li>
              ))}
            </ul>
          </section>

          <div className="mt-12 rounded-xl border border-[#00ffe8]/30 bg-[#00ffe8]/5 p-6 text-center">
            <p className="font-semibold text-white">Try the Visifoot alternative</p>
            <p className="mt-1 text-sm text-zinc-400">AI match predictions with probabilities and scenario analysis</p>
            <Link
              href="/analyse"
              className="mt-4 inline-block rounded-lg bg-[#00ffe8] px-6 py-3 font-semibold text-black hover:opacity-90"
            >
              Use DeepFoot
            </Link>
          </div>
        </main>
      </div>
    </>
  );
}
