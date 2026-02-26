"use client";

type OverUnderItem = { line: string; over_pct: number; under_pct: number };
type ExactScoreItem = { home: number; away: number; probability: number };

type Result = {
  home_team?: string;
  away_team?: string;
  league?: string | null;
  match_date?: string | null;
  venue?: string | null;
  xg_home?: number;
  xg_away?: number;
  xg_total?: number;
  prob_home?: number;
  prob_draw?: number;
  prob_away?: number;
  btts_yes_pct?: number;
  btts_no_pct?: number;
  over_under?: OverUnderItem[];
  exact_scores?: ExactScoreItem[];
  home_form?: string[];
  away_form?: string[];
  home_wdl?: string;
  away_wdl?: string;
  home_form_label?: string;
  away_form_label?: string;
  quick_summary?: string | null;
  scenario_1?: string | null;
  ai_confidence?: string | null;
  attack_home_pct?: number;
  defense_home_pct?: number;
  form_home_pct?: number;
  h2h_home_pct?: number;
  goals_home_pct?: number;
  overall_home_pct?: number;
  [k: string]: unknown;
};

function FormIcon({ result }: { result: string }) {
  if (result === "W") return <span className="text-green-400">✅</span>;
  if (result === "D") return <span className="text-yellow-400">🟡</span>;
  if (result === "L") return <span className="text-red-400">❌</span>;
  return <span className="text-zinc-500">⏳</span>;
}

function StatBar({ label, homePct }: { label: string; homePct?: number }) {
  const pct = Math.min(100, Math.max(0, homePct ?? 50));
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-24 text-zinc-400">{label}</span>
      <div className="flex-1 flex items-center gap-2">
        <div className="flex-1 h-2 bg-dark-input rounded-full overflow-hidden flex">
          <div className="bg-[#00d4ff] h-full rounded-l-full" style={{ width: `${pct}%` }} />
          <div className="bg-[#00f0a0]/30 h-full flex-1 rounded-r-full" />
        </div>
        <span className="text-zinc-300 w-12 text-right">{Math.round(pct)}%</span>
      </div>
      <span className="w-12 text-right text-zinc-500">{100 - Math.round(pct)}%</span>
    </div>
  );
}

export function AnalysisResult({ result }: { result: Result }) {
  const home = result.home_team ?? "Home";
  const away = result.away_team ?? "Away";

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-zinc-500 text-sm">Analyzed match</p>
          <h1 className="text-2xl font-bold text-white mt-1">{home} vs {away}</h1>
          <div className="flex flex-wrap gap-4 mt-3 text-sm text-zinc-400">
            {result.league && <span>🏆 {result.league}</span>}
            {result.match_date && <span>📅 {result.match_date}</span>}
            {result.venue && <span>📍 {result.venue}</span>}
          </div>
        </div>
        <div className="rounded-xl bg-green-500/20 border border-green-500/40 px-4 py-2 text-center">
          <p className="text-green-400 font-semibold">AI analysis ready</p>
          <p className="text-green-300/80 text-xs">Based on stats + football news</p>
        </div>
      </div>

      {/* Recent form */}
      <section className="rounded-2xl bg-dark-card border border-dark-border p-6">
        <div className="flex flex-wrap justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-white">📊 Recent form</h2>
          <span className="text-zinc-500 text-sm">Global form (all competitions)</span>
        </div>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="rounded-xl bg-dark-input p-4">
            <p className="font-medium text-white">{home}</p>
            <p className="text-sm mt-1">{result.home_form_label ? `🔥 ${result.home_form_label}` : "—"}</p>
          </div>
          <div className="rounded-xl bg-dark-input p-4">
            <p className="font-medium text-white">{away}</p>
            <p className="text-sm mt-1">{result.away_form_label ? `📉 ${result.away_form_label}` : "—"}</p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-xl bg-dark-input p-4">
            <p className="font-medium text-white mb-2">{home}</p>
            <p className="text-sm">Form : {result.home_form?.map((r, i) => <FormIcon key={i} result={r} />) ?? "—"}</p>
            <p className="text-sm text-zinc-400 mt-1">V-N-D : {result.home_wdl ?? "—"}</p>
          </div>
          <div className="rounded-xl bg-dark-input p-4">
            <p className="font-medium text-white mb-2">{away}</p>
            <p className="text-sm">Form : {result.away_form?.map((r, i) => <FormIcon key={i} result={r} />) ?? "—"}</p>
            <p className="text-sm text-zinc-400 mt-1">V-N-D : {result.away_wdl ?? "—"}</p>
          </div>
        </div>
      </section>

      {/* Quick summary */}
      {result.quick_summary && (
        <section className="rounded-2xl bg-dark-card border border-dark-border p-6">
          <h2 className="text-lg font-semibold text-white mb-3">🔍 Quick summary</h2>
          <p className="text-zinc-300 leading-relaxed">{result.quick_summary}</p>
          <p className="text-sm text-[#00f0a0]/80 mt-2">Generated from millions of data points and football news.</p>
        </section>
      )}

      {/* Scenario #1 */}
      {result.scenario_1 && (
        <section className="rounded-2xl bg-dark-card border border-dark-border p-6">
          <h2 className="text-lg font-semibold text-white mb-3">📌 Scenario #1</h2>
          <p className="text-zinc-300 leading-relaxed text-sm">{result.scenario_1}</p>
        </section>
      )}

      {/* AI confidence */}
      {result.ai_confidence && (
        <div className="rounded-xl bg-dark-card border border-dark-border px-4 py-3">
          <span className="text-zinc-400 text-sm">🎯 AI confidence </span>
          <span className="text-white font-medium">{result.ai_confidence}</span>
          <p className="text-zinc-500 text-xs mt-0.5">Confidence level based on available data quality.</p>
        </div>
      )}

      {/* Exact probabilities 1X2 */}
      <section className="rounded-2xl bg-dark-card border border-dark-border p-6">
        <h2 className="text-lg font-semibold text-white mb-4">📊 Exact probabilities</h2>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="rounded-xl bg-dark-input p-4">
            <p className="text-zinc-400 text-sm">{home} win</p>
            <p className="text-2xl font-bold text-[#00d4ff]">{result.prob_home ?? 0}%</p>
          </div>
          <div className="rounded-xl bg-dark-input p-4">
            <p className="text-zinc-400 text-sm">Draw</p>
            <p className="text-2xl font-bold text-yellow-400">{result.prob_draw ?? 0}%</p>
          </div>
          <div className="rounded-xl bg-dark-input p-4">
            <p className="text-zinc-400 text-sm">{away} win</p>
            <p className="text-2xl font-bold text-[#00f0a0]">{result.prob_away ?? 0}%</p>
          </div>
        </div>
      </section>

      {/* Statistical comparison */}
      <section className="rounded-2xl bg-dark-card border border-dark-border p-6">
        <h2 className="text-lg font-semibold text-white mb-4">📊 Statistical comparison</h2>
        <div className="space-y-4">
          <StatBar label="Attack" homePct={result.attack_home_pct} />
          <StatBar label="Defense" homePct={result.defense_home_pct} />
          <StatBar label="Form" homePct={result.form_home_pct} />
          <StatBar label="H2H" homePct={result.h2h_home_pct} />
          <StatBar label="Goals" homePct={result.goals_home_pct} />
          <StatBar label="Overall" homePct={result.overall_home_pct} />
        </div>
      </section>

      {/* Our predictions */}
      <section className="rounded-2xl bg-dark-card border border-dark-border p-6">
        <h2 className="text-lg font-semibold text-white mb-4">🎯 Our predictions</h2>
        <div className="grid grid-cols-3 gap-4 mb-6 text-center">
          <div>
            <p className="text-zinc-400 text-sm">{home}</p>
            <p className="text-xl font-bold text-white">{result.xg_home ?? 0} goals</p>
          </div>
          <div>
            <p className="text-zinc-400 text-sm">{away}</p>
            <p className="text-xl font-bold text-white">{result.xg_away ?? 0} goals</p>
          </div>
          <div>
            <p className="text-zinc-400 text-sm">Total</p>
            <p className="text-xl font-bold text-[#00f0a0]">{result.xg_total ?? 0} goals</p>
          </div>
        </div>
        <div className="mb-6">
          <p className="text-zinc-400 text-sm mb-2">Both teams to score</p>
          <div className="flex gap-4">
            <span className="text-green-400">Yes {result.btts_yes_pct ?? 0}%</span>
            <span className="text-zinc-400">No {result.btts_no_pct ?? 0}%</span>
          </div>
        </div>
        <div>
          <p className="text-zinc-400 text-sm mb-3">Goal count probabilities</p>
          <div className="space-y-2">
            {result.over_under?.map((row) => (
              <div key={row.line} className="flex justify-between text-sm">
                <span>Over {row.line} goals / Under {row.line} goals</span>
                <span><span className="text-[#00d4ff]">{row.over_pct}%</span> / <span className="text-zinc-400">{row.under_pct}%</span></span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Exact scores */}
      {result.exact_scores && result.exact_scores.length > 0 && (
        <section className="rounded-2xl bg-dark-card border border-dark-border p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Score exact (top 5)</h2>
          <div className="flex flex-wrap gap-3">
            {result.exact_scores.map((s, i) => (
              <span key={i} className="rounded-lg bg-dark-input px-3 py-2 text-sm">
                {s.home}-{s.away} <span className="text-[#00d4ff]">{s.probability}%</span>
              </span>
            ))}
          </div>
        </section>
      )}

      <p className="text-center text-zinc-500 text-xs">This analysis is provided for informational purposes only.</p>
    </div>
  );
}
