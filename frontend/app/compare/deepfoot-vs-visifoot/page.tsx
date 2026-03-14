import Link from "next/link";
import { buildPageMetadata } from "@/lib/seo/metadata";
import { faqPageSchema, breadcrumbSchema } from "@/lib/seo/schema";
import { SITE_URL } from "@/lib/seo/site";

export const metadata = buildPageMetadata({
  title: "DeepFoot vs Visifoot: Which AI Football Predictor Is Better?",
  description:
    "Compare DeepFoot and Visifoot: AI football prediction models, probability outputs, league coverage, and analysis depth. Choose the right tool for match predictions.",
  path: "/compare/deepfoot-vs-visifoot",
});

const FAQ = [
  {
    question: "What is the main difference between DeepFoot and Visifoot?",
    answer:
      "DeepFoot focuses on explicit win/draw/loss probabilities, over/under, BTTS, and scenario analysis with transparent reasoning. Both use AI; DeepFoot emphasizes probability outputs and data-driven match analysis across 27 European leagues.",
  },
  {
    question: "Does DeepFoot offer free predictions?",
    answer:
      "Yes. You can run AI match analyses and see probability-based predictions. Premium plans unlock more analyses and advanced insights.",
  },
  {
    question: "Which tool is better for betting analysis?",
    answer:
      "DeepFoot is built for bettors who want clear probabilities (1X2, over/under, BTTS) and scenario breakdowns. Use the comparison table above to see which outputs matter most for your use case.",
  },
  {
    question: "Can I use DeepFoot for any league?",
    answer:
      "DeepFoot covers 27 major European leagues including Premier League, La Liga, Serie A, Bundesliga, and Champions League. Check the analyse page for the full list.",
  },
];

export default function DeepfootVsVisifootPage() {
  const breadcrumb = breadcrumbSchema([
    { name: "Home", path: "/" },
    { name: "Compare", path: "/compare/deepfoot-vs-visifoot" },
    { name: "DeepFoot vs Visifoot", path: "/compare/deepfoot-vs-visifoot" },
  ]);
  const faqSchema = faqPageSchema(FAQ, `${SITE_URL}/compare/deepfoot-vs-visifoot`);

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
            <span className="text-zinc-300">DeepFoot vs Visifoot</span>
          </nav>

          <h1 className="text-3xl font-bold text-white sm:text-4xl">
            DeepFoot vs Visifoot: Which AI Football Predictor Is Better?
          </h1>
          <p className="mt-4 text-lg text-zinc-400">
            Both tools use AI for football match analysis. Here we compare prediction outputs, data coverage, and use cases so you can choose the right one.
          </p>

          <section className="mt-10">
            <h2 className="text-xl font-bold text-white">Quick comparison</h2>
            <div className="mt-4 overflow-x-auto rounded-xl border border-white/10 bg-white/5">
              <table className="w-full min-w-[600px] text-left text-sm">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="p-4 font-semibold text-white">Feature</th>
                    <th className="p-4 font-semibold text-white">DeepFoot</th>
                    <th className="p-4 font-semibold text-white">Visifoot</th>
                  </tr>
                </thead>
                <tbody className="text-zinc-300">
                  <tr className="border-b border-white/5">
                    <td className="p-4">1X2 probabilities</td>
                    <td className="p-4">Yes, explicit %</td>
                    <td className="p-4">Yes</td>
                  </tr>
                  <tr className="border-b border-white/5">
                    <td className="p-4">Over/Under</td>
                    <td className="p-4">Yes</td>
                    <td className="p-4">Yes</td>
                  </tr>
                  <tr className="border-b border-white/5">
                    <td className="p-4">BTTS (Both Teams to Score)</td>
                    <td className="p-4">Yes</td>
                    <td className="p-4">Yes</td>
                  </tr>
                  <tr className="border-b border-white/5">
                    <td className="p-4">Scenario / key factors</td>
                    <td className="p-4">Yes, AI-written</td>
                    <td className="p-4">Yes</td>
                  </tr>
                  <tr className="border-b border-white/5">
                    <td className="p-4">League coverage</td>
                    <td className="p-4">27 European leagues</td>
                    <td className="p-4">Major European leagues</td>
                  </tr>
                  <tr className="border-b border-white/5">
                    <td className="p-4">Data + news</td>
                    <td className="p-4">Stats + football news linked</td>
                    <td className="p-4">Stats + context</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section className="mt-10">
            <h2 className="text-xl font-bold text-white">When to use DeepFoot</h2>
            <ul className="mt-4 list-inside list-disc space-y-2 text-zinc-300">
              <li>You want clear win/draw/loss probabilities and over/under percentages.</li>
              <li>You care about scenario analysis and key factors in plain language.</li>
              <li>You follow multiple European leagues and want one place for predictions.</li>
              <li>You prefer a tool that links predictions to recent football news and stats.</li>
            </ul>
          </section>

          <section className="mt-10">
            <h2 className="text-xl font-bold text-white">When to use Visifoot</h2>
            <ul className="mt-4 list-inside list-disc space-y-2 text-zinc-300">
              <li>You already use Visifoot and are satisfied with its interface and outputs.</li>
              <li>You want to compare several predictors; using both DeepFoot and Visifoot is valid for cross-checking.</li>
            </ul>
          </section>

          <section className="mt-10">
            <h2 className="text-xl font-bold text-white">Bottom line</h2>
            <p className="mt-4 text-zinc-300">
              DeepFoot and Visifoot are both AI football prediction tools. DeepFoot emphasizes explicit probabilities, scenario analysis, and coverage of 27 European leagues. Try{" "}
              <Link href="/analyse" className="text-[#00ffe8] hover:opacity-90">
                DeepFoot’s AI analysis
              </Link>{" "}
              for free and compare the outputs with your current workflow.
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
            <p className="font-semibold text-white">Get AI match predictions in seconds</p>
            <p className="mt-1 text-sm text-zinc-400">Enter two teams and see probabilities + analysis</p>
            <Link
              href="/analyse"
              className="mt-4 inline-block rounded-lg bg-[#00ffe8] px-6 py-3 font-semibold text-black hover:opacity-90"
            >
              Try DeepFoot
            </Link>
          </div>
        </main>
      </div>
    </>
  );
}
