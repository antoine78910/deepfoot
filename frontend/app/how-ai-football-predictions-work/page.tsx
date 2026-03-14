import Link from "next/link";
import { buildPageMetadata } from "@/lib/seo/metadata";
import { faqPageSchema, breadcrumbSchema } from "@/lib/seo/schema";
import { SITE_URL } from "@/lib/seo/site";

export const metadata = buildPageMetadata({
  title: "How AI Football Predictions Work",
  description:
    "How AI predicts football matches: data sources, probability models, and accuracy. Learn what goes into AI match prediction and how to use it wisely.",
  path: "/how-ai-football-predictions-work",
});

const FAQ = [
  {
    question: "How accurate are AI football predictions?",
    answer:
      "AI models estimate probabilities, not certainties. Accuracy depends on data quality, model design, and the league. No model can guarantee results; use predictions as one input among many.",
  },
  {
    question: "What data is used for match prediction?",
    answer:
      "Typical inputs include team form, head-to-head history, goals and xG, home/away performance, and sometimes injuries or news. DeepFoot uses stats and football news from the same providers used by major sports media.",
  },
  {
    question: "Can AI really predict football matches?",
    answer:
      "AI can estimate win/draw/loss and goals probabilities from historical and current data. It cannot account for every factor (referee, motivation, luck). Treat outputs as probabilistic estimates, not guarantees.",
  },
  {
    question: "Are AI predictions better than bookmakers?",
    answer:
      "Bookmaker odds reflect market consensus and margin. AI models can sometimes spot value when their probabilities differ from odds. Comparing both is useful; neither is infallible.",
  },
  {
    question: "Which leagues does DeepFoot cover?",
    answer:
      "DeepFoot covers 27 major European leagues including Premier League, La Liga, Serie A, Bundesliga, Ligue 1, and Champions League.",
  },
];

export default function HowAiFootballPredictionsWorkPage() {
  const breadcrumb = breadcrumbSchema([
    { name: "Home", path: "/" },
    { name: "AI Football Predictions", path: "/ai-football-predictions" },
    { name: "How AI Football Predictions Work", path: "/how-ai-football-predictions-work" },
  ]);
  const faqSchema = faqPageSchema(FAQ, `${SITE_URL}/how-ai-football-predictions-work`);

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
              Try predictions
            </Link>
          </div>
        </header>

        <main className="mx-auto max-w-4xl px-4 py-10 sm:py-14">
          <nav className="mb-6 text-sm text-zinc-400">
            <Link href="/" className="hover:text-white">Home</Link>
            <span className="mx-2">/</span>
            <Link href="/ai-football-predictions" className="hover:text-white">AI Football Predictions</Link>
            <span className="mx-2">/</span>
            <span className="text-zinc-300">How they work</span>
          </nav>

          <h1 className="text-3xl font-bold text-white sm:text-4xl">
            How AI Football Predictions Work
          </h1>
          <p className="mt-4 text-lg text-zinc-400">
            AI football prediction tools use team stats, form, and sometimes news to estimate match outcomes. Here’s what goes into them and how to use the outputs.
          </p>

          <section className="mt-10">
            <h2 className="text-xl font-bold text-white">What AI prediction models use</h2>
            <p className="mt-4 text-zinc-300">
              Modern match prediction models typically combine:
            </p>
            <ul className="mt-4 list-inside list-disc space-y-2 text-zinc-300">
              <li><strong className="text-white">Team form</strong> — Recent results (e.g. last 5 matches) and trends.</li>
              <li><strong className="text-white">Head-to-head</strong> — Historical results between the two teams.</li>
              <li><strong className="text-white">Goals and xG</strong> — Goals scored/conceded and expected goals.</li>
              <li><strong className="text-white">Home/away performance</strong> — Venue effects.</li>
              <li><strong className="text-white">League context</strong> — Level and style of the competition.</li>
            </ul>
            <p className="mt-4 text-zinc-300">
              Some systems also use news (injuries, lineup hints) when available. DeepFoot links analyses to football news from the same providers used by major sports media.
            </p>
          </section>

          <section className="mt-10">
            <h2 className="text-xl font-bold text-white">Probability outputs</h2>
            <p className="mt-4 text-zinc-300">
              Good AI predictors output <strong className="text-white">probabilities</strong>, not single “tips”. You’ll see percentages for home win, draw, away win, and often over/under or both teams to score. These are estimates of likelihood, not guarantees. Football remains unpredictable; use probabilities to compare with odds and assess value, not as certainties.
            </p>
          </section>

          <section className="mt-10">
            <h2 className="text-xl font-bold text-white">Accuracy and limits</h2>
            <p className="mt-4 text-zinc-300">
              No model can capture every factor (referee, motivation, luck, last-minute events). Accuracy varies by league and time horizon. Best practice: use AI predictions as one input, combine with your own research, and never treat any tool as a guarantee of results.
            </p>
          </section>

          <section className="mt-10">
            <h2 className="text-xl font-bold text-white">How to use DeepFoot</h2>
            <p className="mt-4 text-zinc-300">
              DeepFoot gives you 1X2 probabilities, over/under, BTTS, and a short scenario analysis. Enter two teams on the{" "}
              <Link href="/analyse" className="text-[#00ffe8] hover:opacity-90">
                analyse page
              </Link>
              {" "}to get an AI-generated summary and key factors. Coverage includes 27 European leagues.
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
            <p className="font-semibold text-white">See AI predictions in action</p>
            <Link
              href="/analyse"
              className="mt-4 inline-block rounded-lg bg-[#00ffe8] px-6 py-3 font-semibold text-black hover:opacity-90"
            >
              Analyse a match
            </Link>
          </div>
        </main>
      </div>
    </>
  );
}
