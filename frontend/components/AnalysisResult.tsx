"use client";

import { useLanguage } from "@/contexts/LanguageContext";

type OverUnderItem = { line: string; over_pct: number; under_pct: number };
type ExactScoreItem = { home: number; away: number; probability: number };

type Result = {
  home_team?: string;
  away_team?: string;
  league?: string | null;
  match_date?: string | null;
  venue?: string | null;
  home_team_logo?: string | null;
  away_team_logo?: string | null;
  xg_home?: number;
  xg_away?: number;
  xg_total?: number;
  prob_home?: number;
  prob_draw?: number;
  prob_away?: number;
  implied_odds_home?: number;
  implied_odds_draw?: number;
  implied_odds_away?: number;
  most_likely_score?: { home: number; away: number; probability: number };
  total_goals_distribution?: Record<string, number>;
  goal_difference_dist?: Record<string, number>;
  double_chance_1x?: number;
  double_chance_x2?: number;
  double_chance_12?: number;
  asian_handicap?: { home_neg1_pct: number; home_plus1_pct: number; away_neg1_pct: number; away_plus1_pct: number };
  upset_probability?: number;
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
  scenario_2?: { title?: string; body?: string; probability_pct?: number | null } | null;
  scenario_3?: { title?: string; body?: string; probability_pct?: number | null } | null;
  scenario_4?: { title?: string; body?: string; probability_pct?: number | null } | null;
  key_forces_home?: string[] | null;
  key_forces_away?: string[] | null;
  ai_confidence?: string | null;
  attack_home_pct?: number;
  defense_home_pct?: number;
  form_home_pct?: number;
  h2h_home_pct?: number;
  goals_home_pct?: number;
  overall_home_pct?: number;
  [k: string]: unknown;
};

/** Grand indicateur de forme (Great = flamme orange, Poor = graph violet/rose, Average = barres) */
function FormLabelBlock({ label }: { label: string }) {
  const l = (label || "").toLowerCase();
  const isGreat = l.includes("great") || l.includes("bonne") || l.includes("excellent");
  const isPoor = l.includes("poor") || l.includes("faible") || l.includes("difficile");
  const isAverage = l.includes("average") || l.includes("moyenne") || l.includes("moyen");
  return (
    <div className="flex items-center gap-3">
      {isGreat && (
        <span className="text-3xl" title="Great form">🔥</span>
      )}
      {isPoor && (
        <span className="text-2xl" title="Poor form">📉</span>
      )}
      {isAverage && !isGreat && !isPoor && (
        <span className="text-2xl" title="Average form">📊</span>
      )}
      {!isGreat && !isPoor && !isAverage && <span className="text-2xl">📊</span>}
      <span className="font-semibold text-white">{label || "—"}</span>
    </div>
  );
}

function AppleCheck() {
  return (
    <span className="inline-flex items-center justify-center w-6 h-6 flex-shrink-0" title="Victoire" aria-hidden>✅</span>
  );
}

function AppleCross() {
  return (
    <span className="inline-flex items-center justify-center w-6 h-6 flex-shrink-0" title="Défaite" aria-hidden>❌</span>
  );
}

function AppleDraw() {
  return (
    <span className="inline-flex items-center justify-center w-6 h-6 flex-shrink-0" title="Nul" aria-hidden>➖</span>
  );
}

function FormIcon({ result }: { result: string }) {
  if (result === "W") return <AppleCheck />;
  if (result === "D") return <AppleDraw />;
  if (result === "L") return <AppleCross />;
  return <span className="inline-flex w-6 h-6 items-center justify-center rounded border border-zinc-500/50 text-zinc-500 text-xs flex-shrink-0" title="À venir">?</span>;
}

function StatBar({
  label,
  homePct,
  homeColor = "text-zinc-300",
  awayColor = "text-zinc-300",
}: {
  label: string;
  homePct?: number;
  homeColor?: string;
  awayColor?: string;
}) {
  const pct = Math.min(100, Math.max(0, homePct ?? 50));
  const awayPct = 100 - Math.round(pct);
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-zinc-400">
        <span className={`tabular-nums ${homeColor}`}>{Math.round(pct)}%</span>
        <span className="font-medium text-zinc-300">{label}</span>
        <span className={`tabular-nums ${awayColor}`}>{awayPct}%</span>
      </div>
      <div className="h-3 bg-[#1c1c28] rounded-full overflow-hidden flex shadow-inner">
        <div className="h-full rounded-l-full transition-all duration-300" style={{ width: `${pct}%`, background: HOME_HEX }} />
        <div className="h-full flex-1 rounded-r-full opacity-80" style={{ background: AWAY_HEX }} />
      </div>
    </div>
  );
}

/** Barre à deux segments (gauche % / droite %) avec labels et couleurs */
function SplitBar({
  leftPct,
  leftLabel,
  rightLabel,
  leftColor = "bg-[#00ffe8]",
  rightColor = "bg-[#ef4444]/60",
}: {
  leftPct: number;
  leftLabel: string;
  rightLabel: string;
  leftColor?: string;
  rightColor?: string;
}) {
  const pct = Math.min(100, Math.max(0, leftPct));
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-sm">
        <span className="text-zinc-300">{leftLabel}</span>
        <span className="text-zinc-300">{rightLabel}</span>
      </div>
      <div className="h-3 bg-dark-input rounded-full overflow-hidden flex">
        <div className={`${leftColor} h-full rounded-l-full transition-all`} style={{ width: `${pct}%` }} />
        <div className={`${rightColor} h-full flex-1 rounded-r-full`} />
      </div>
      <div className="flex justify-between text-xs text-zinc-500">
        <span>{Math.round(pct)}%</span>
        <span>{Math.round(100 - pct)}%</span>
      </div>
    </div>
  );
}

function TrophyIcon() {
  return (
    <svg className="w-4 h-4 text-zinc-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7" />
    </svg>
  );
}
function CalendarIcon() {
  return (
    <svg className="w-4 h-4 text-zinc-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  );
}
function LocationIcon() {
  return (
    <svg className="w-4 h-4 text-zinc-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );
}

/* Domicile = accent adouci, Extérieur = rouge adouci */
const HOME_HEX = "#22c5ba";
const AWAY_HEX = "#f97373";
const HOME_COLOR = "text-[#00ffe8]";
const AWAY_COLOR = "text-[#ef4444]";
const FLASHY_GOLD = "text-[#eab308]";
const FLASHY_RED = "text-[#ef4444]";
const FLASHY_BLUE = "text-[#00ffe8]";

export function AnalysisResult({ result }: { result: Result }) {
  const home = result.home_team ?? "Home";
  const away = result.away_team ?? "Away";
  const { t } = useLanguage();

  return (
    <div className="space-y-8">
      {/* Recap card - style flashy */}
      <div className="rounded-2xl bg-[#14141c] border border-white/10 p-6 shadow-lg">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4 min-w-0 flex-1">
            {result.home_team_logo ? (
              <img src={result.home_team_logo} alt="" className="w-14 h-14 object-contain flex-shrink-0" />
            ) : (
              <div className="w-14 h-14 rounded-xl bg-[#1c1c28] flex-shrink-0 flex items-center justify-center text-white font-bold">{home.slice(0, 2)}</div>
            )}
            <div className="min-w-0">
              <p className="text-zinc-500 text-sm">{t("analysis.analyzedMatch")}</p>
              <h1 className="text-xl md:text-2xl font-bold mt-0.5 text-white">
                <span className="text-white">{home}</span>
                <span className="text-zinc-500 font-normal mx-2">vs</span>
                <span className="text-white">{away}</span>
              </h1>
            </div>
            {result.away_team_logo ? (
              <img src={result.away_team_logo} alt="" className="w-14 h-14 object-contain flex-shrink-0" />
            ) : (
              <div className="w-14 h-14 rounded-xl bg-[#1c1c28] flex-shrink-0 flex items-center justify-center text-white font-bold">{away.slice(0, 2)}</div>
            )}
          </div>
          <div className="rounded-lg border border-[#00ffe8]/60 px-4 py-2 text-center flex-shrink-0">
            <p className="text-[#00ffe8] font-semibold text-sm">{t("analysis.aiReady")}</p>
            <p className="text-[#00ffe8]/80 text-xs mt-0.5">{t("analysis.basedOn")}</p>
          </div>
        </div>
        {(result.league || result.match_date || result.venue) && (
          <div className="mt-5 pt-4 border-t border-white/10 flex flex-wrap gap-x-6 gap-y-1 text-sm text-white">
            {result.league && (
              <p className="flex items-center gap-2">
                <span className={FLASHY_GOLD}>🏆</span>
                {result.league}
              </p>
            )}
            {result.match_date && (
              <p className="flex items-center gap-2 text-zinc-400">
                <span>📅</span>
                {result.match_date}
              </p>
            )}
            {result.venue && (
              <p className="flex items-center gap-2">
                <span className={FLASHY_RED}>📍</span>
                {result.venue}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Recent form - style flashy avec gros indicateurs */}
      <section className="rounded-2xl bg-[#14141c] border border-white/10 p-6">
        <div className="flex flex-wrap justify-between items-center mb-5">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <span className="text-zinc-400">📊</span> {t("analysis.recentForm")}
          </h2>
          <span className="text-zinc-500 text-sm">{t("analysis.globalForm")}</span>
        </div>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="rounded-xl bg-[#1c1c28] border border-white/5 p-5 flex items-center gap-4">
            {result.home_team_logo ? (
              <img src={result.home_team_logo} alt="" className="w-12 h-12 object-contain flex-shrink-0" />
            ) : (
              <div className="w-12 h-12 rounded-lg bg-dark-input flex-shrink-0 flex items-center justify-center text-white font-bold text-sm">{home.slice(0, 2)}</div>
            )}
            <div className="min-w-0">
              <p className="font-semibold text-white">{home}</p>
              <div className="mt-2">
                <FormLabelBlock label={result.home_form_label ?? ""} />
              </div>
            </div>
          </div>
          <div className="rounded-xl bg-[#1c1c28] border border-white/5 p-5 flex items-center gap-4">
            {result.away_team_logo ? (
              <img src={result.away_team_logo} alt="" className="w-12 h-12 object-contain flex-shrink-0" />
            ) : (
              <div className="w-12 h-12 rounded-lg bg-dark-input flex-shrink-0 flex items-center justify-center text-white font-bold text-sm">{away.slice(0, 2)}</div>
            )}
            <div className="min-w-0">
              <p className="font-semibold text-white">{away}</p>
              <div className="mt-2">
                <FormLabelBlock label={result.away_form_label ?? ""} />
              </div>
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-xl bg-[#1c1c28] border border-white/5 p-4">
            <p className="text-sm text-zinc-300 flex items-center gap-1 flex-wrap">
              {result.home_form?.map((r, i) => <FormIcon key={i} result={r} />) ?? "—"}
            </p>
            <p className="text-sm text-zinc-400 mt-1">V-N-D : {result.home_wdl ?? "—"}</p>
          </div>
          <div className="rounded-xl bg-[#1c1c28] border border-white/5 p-4">
            <p className="text-sm text-zinc-300 flex items-center gap-1 flex-wrap">
              {result.away_form?.map((r, i) => <FormIcon key={i} result={r} />) ?? "—"}
            </p>
            <p className="text-sm text-zinc-400 mt-1">V-N-D : {result.away_wdl ?? "—"}</p>
          </div>
        </div>
      </section>

      {/* Quick summary - icône bulle bleue */}
      {result.quick_summary && (
        <section className="rounded-2xl bg-[#14141c] border border-white/10 p-6">
          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <span className="text-[#00ffe8]">🔍</span> {t("analysis.summary")}
          </h2>
          <p className="text-zinc-300 leading-relaxed">{result.quick_summary}</p>
          <p className="text-sm text-[#00ffe8] mt-2">Generated from millions of data points and football news.</p>
        </section>
      )}

      {/* Scenario #1 */}
      {result.scenario_1 && (
        <section className="rounded-2xl bg-[#14141c] border border-white/10 p-6">
          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <span>📌</span> {t("analysis.scenario")}
          </h2>
          <p className="text-zinc-300 leading-relaxed text-sm">{result.scenario_1}</p>
        </section>
      )}

      {/* AI confidence — barre de progression */}
      {result.ai_confidence && (() => {
        const label = String(result.ai_confidence).trim();
        const confLower = label.toLowerCase();
        const pct = confLower.includes("very high") || confLower.includes("très élevé") ? 92
          : confLower.includes("high") || confLower.includes("élevé") ? 75
          : confLower.includes("medium") || confLower.includes("moyen") ? 50
          : confLower.includes("low") || confLower.includes("faible") ? 28
          : 60;
        return (
          <div className="rounded-xl bg-[#14141c] border border-white/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-zinc-400 text-sm font-medium">🎯 AI confidence</span>
              <svg className="w-5 h-5 text-rose-400/90 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 9 9 0 0 0 6.003 5.997 9 9 0 0 0 6.003-5.997 4 4 0 0 0-2.526-5.77 3 3 0 0 0-5.997-.125z" />
              </svg>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex-1 h-3 bg-dark-input rounded-full overflow-hidden">
                <div className="h-full bg-[#00ffe8] rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
              </div>
              <span className="text-zinc-300 text-sm font-medium whitespace-nowrap">{label}</span>
            </div>
            <p className="text-zinc-500 text-xs mt-1.5">Confidence level based on available data quality.</p>
          </div>
        );
      })()}

      {/* Exact probabilities — barres 1X2 + cotes implicites */}
      <section className="rounded-2xl bg-[#14141c] border border-white/10 p-6">
        <div className="flex items-center gap-2 mb-4">
          <h2 className="text-lg font-semibold text-white">📊 Exact probabilities</h2>
        </div>
        <div className="space-y-4 mb-4">
          <div className="flex items-center gap-4">
            <span className="text-zinc-300 text-sm w-28 flex-shrink-0">{home} win</span>
            <div className="flex-1 h-3 bg-dark-input rounded-full overflow-hidden min-w-0">
              <div className="h-full bg-[#00ffe8] rounded-full transition-all duration-500" style={{ width: `${result.prob_home ?? 0}%` }} />
            </div>
            <span className="text-[#00ffe8] font-semibold text-sm w-10 text-right flex-shrink-0">{result.prob_home ?? 0}%</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-zinc-300 text-sm w-28 flex-shrink-0">Draw</span>
            <div className="flex-1 h-3 bg-dark-input rounded-full overflow-hidden min-w-0">
              <div className="h-full bg-[#00ffe8] rounded-full transition-all duration-500" style={{ width: `${result.prob_draw ?? 0}%` }} />
            </div>
            <span className="text-zinc-300 font-semibold text-sm w-10 text-right flex-shrink-0">{result.prob_draw ?? 0}%</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-zinc-300 text-sm w-28 flex-shrink-0">{away} win</span>
            <div className="flex-1 h-3 bg-dark-input rounded-full overflow-hidden min-w-0">
              <div className="h-full bg-[#00ffe8] rounded-full transition-all duration-500" style={{ width: `${result.prob_away ?? 0}%` }} />
            </div>
            <span className="text-[#ef4444] font-semibold text-sm w-10 text-right flex-shrink-0">{result.prob_away ?? 0}%</span>
          </div>
        </div>
        {result.implied_odds_home != null && (
          <>
            <p className="text-zinc-500 text-xs mb-2">{t("betting.impliedOdds")} (decimal, compare with bookmakers)</p>
            <div className="flex flex-wrap gap-4 text-xs text-zinc-500">
              <span>{home} ~{result.implied_odds_home}</span>
              <span>Draw ~{result.implied_odds_draw ?? "—"}</span>
              <span>{away} ~{result.implied_odds_away ?? "—"}</span>
            </div>
          </>
        )}
      </section>

      {/* Score le plus probable + distribution buts + écart */}
      {(result.most_likely_score || result.total_goals_distribution || result.goal_difference_dist) && (
        <section className="rounded-2xl bg-[#14141c] border border-white/10 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">🎯 {t("betting.mostLikelyScore")} & distributions</h2>
          {result.most_likely_score && (
            <div className="mb-4">
              <p className="text-zinc-400 text-sm mb-1">{t("betting.mostLikelyScore")}</p>
              <p className="text-xl font-bold text-white">{result.most_likely_score.home}-{result.most_likely_score.away} <span className="text-[#00ffe8]">({result.most_likely_score.probability}%)</span></p>
              <p className="text-zinc-500 text-xs mt-1">Expected: {result.xg_home ?? 0} – {result.xg_away ?? 0} (xG)</p>
            </div>
          )}
          {result.total_goals_distribution && (
            <div className="mb-4">
              <p className="text-zinc-400 text-sm mb-2">{t("betting.totalGoalsDist")}</p>
              <div className="flex flex-wrap gap-3">
                {(() => {
                  const dist = result.total_goals_distribution;
                  return ["0", "1", "2", "3+"].map((k) => (
                  <span key={k} className="rounded-lg bg-dark-input px-3 py-1.5 text-sm">
                    {k} buts: <span className="text-[#00ffe8]">{dist?.[k] ?? 0}%</span>
                  </span>
                  ));
                })()}
              </div>
            </div>
          )}
          {result.goal_difference_dist && (
            <div>
              <p className="text-zinc-400 text-sm mb-2">{t("betting.goalDiffDist")}</p>
              <div className="flex flex-wrap gap-3">
                <span className="rounded-lg bg-dark-input px-3 py-1.5 text-sm">{t("betting.diff1")}: <span className="text-[#00ffe8]">{result.goal_difference_dist["1"] ?? 0}%</span></span>
                <span className="rounded-lg bg-dark-input px-3 py-1.5 text-sm">{t("betting.diff2")}: <span className="text-[#00ffe8]">{result.goal_difference_dist["2"] ?? 0}%</span></span>
                <span className="rounded-lg bg-dark-input px-3 py-1.5 text-sm">{t("betting.diff3plus")}: <span className="text-[#00ffe8]">{result.goal_difference_dist["3+"] ?? 0}%</span></span>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Double chance + Asian handicap + Upset */}
      {(result.double_chance_1x != null || result.asian_handicap || result.upset_probability != null) && (
        <section className="rounded-2xl bg-[#14141c] border border-white/10 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">📌 {t("betting.doubleChance")} & markets</h2>
          {result.double_chance_1x != null && (
            <div className="mb-4">
              <p className="text-zinc-400 text-sm mb-2">{t("betting.doubleChance")}</p>
              <div className="flex flex-wrap gap-4">
                <span className="rounded-lg bg-dark-input px-3 py-2 text-sm">1X: <strong className="text-white">{result.double_chance_1x}%</strong></span>
                <span className="rounded-lg bg-dark-input px-3 py-2 text-sm">X2: <strong className="text-white">{result.double_chance_x2 ?? 0}%</strong></span>
                <span className="rounded-lg bg-dark-input px-3 py-2 text-sm">12: <strong className="text-white">{result.double_chance_12 ?? 0}%</strong></span>
              </div>
            </div>
          )}
          {result.asian_handicap && (
            <div className="mb-4">
              <p className="text-zinc-400 text-sm mb-2">{t("betting.asianHandicap")}</p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="rounded-lg bg-dark-input px-3 py-2"><span className="text-white font-semibold">{home}</span> -1: <span className="text-[#00ffe8] font-medium">{result.asian_handicap.home_neg1_pct}%</span></div>
                <div className="rounded-lg bg-dark-input px-3 py-2"><span className="text-white font-semibold">{home}</span> +1: <span className="text-[#00ffe8] font-medium">{result.asian_handicap.home_plus1_pct}%</span></div>
                <div className="rounded-lg bg-dark-input px-3 py-2"><span className="text-white font-semibold">{away}</span> -1: <span className="text-[#ef4444] font-medium">{result.asian_handicap.away_neg1_pct}%</span></div>
                <div className="rounded-lg bg-dark-input px-3 py-2"><span className="text-white font-semibold">{away}</span> +1: <span className="text-[#ef4444] font-medium">{result.asian_handicap.away_plus1_pct}%</span></div>
              </div>
            </div>
          )}
          {result.upset_probability != null && (
            <div>
              <p className="text-zinc-400 text-sm mb-1">{t("betting.upsetProb")}</p>
              <p className="text-lg font-semibold text-[#ef4444]">{result.upset_probability}%</p>
            </div>
          )}
        </section>
      )}

      {/* Statistical comparison - bleu = domicile, rouge = extérieur */}
      <section className="rounded-2xl bg-[#14141c] border border-white/10 p-6">
        <h2 className="text-lg font-semibold text-white mb-2">📊 {t("analysis.statisticalComparison")}</h2>
        <div className="flex justify-between text-sm font-semibold mb-3 px-1">
          <span className={HOME_COLOR}>{home}</span>
          <span className={AWAY_COLOR}>{away}</span>
        </div>
        <div className="space-y-5">
          <StatBar label="Attack" homePct={result.attack_home_pct} homeColor={HOME_COLOR} awayColor={AWAY_COLOR} />
          <StatBar label="Defense" homePct={result.defense_home_pct} homeColor={HOME_COLOR} awayColor={AWAY_COLOR} />
          <StatBar label="Form" homePct={result.form_home_pct} homeColor={HOME_COLOR} awayColor={AWAY_COLOR} />
          <StatBar label="H2H" homePct={result.h2h_home_pct} homeColor={HOME_COLOR} awayColor={AWAY_COLOR} />
          <StatBar label="Goals" homePct={result.goals_home_pct} homeColor={HOME_COLOR} awayColor={AWAY_COLOR} />
          <StatBar label="Overall" homePct={result.overall_home_pct} homeColor={HOME_COLOR} awayColor={AWAY_COLOR} />
        </div>
      </section>

      {/* Our predictions */}
      <section className="rounded-2xl bg-[#14141c] border border-white/10 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">🎯 Our predictions</h2>
        <div className="space-y-4 mb-6">
          {typeof result.xg_home === "number" && typeof result.xg_away === "number" && (result.xg_home + result.xg_away > 0) && (
            <StatBar
              label="xG share"
              homePct={(result.xg_home / (result.xg_home + result.xg_away)) * 100}
              homeColor={HOME_COLOR}
              awayColor={AWAY_COLOR}
            />
          )}
          {typeof result.btts_yes_pct === "number" && (
            <StatBar
              label="BTTS Yes"
              homePct={result.btts_yes_pct}
              homeColor={HOME_COLOR}
              awayColor={AWAY_COLOR}
            />
          )}
          {result.over_under && result.over_under.length > 0 && (
            <StatBar
              label="Over 2.5"
              homePct={(result.over_under.find((r) => r.line === "2.5") ?? result.over_under[0]).over_pct}
              homeColor={HOME_COLOR}
              awayColor={AWAY_COLOR}
            />
          )}
        </div>
        <p className="text-xs text-zinc-500">
          Home xG {typeof result.xg_home === "number" ? result.xg_home.toFixed(2) : "0"} – Away xG{" "}
          {typeof result.xg_away === "number" ? result.xg_away.toFixed(2) : "0"} (total{" "}
          {typeof result.xg_total === "number" ? result.xg_total.toFixed(2) : "0"} goals). BTTS Yes{" "}
          {typeof result.btts_yes_pct === "number" ? result.btts_yes_pct.toFixed(1) : "0"}%.
        </p>
      </section>

      {/* Exact scores */}
      {result.exact_scores && result.exact_scores.length > 0 && (
        <section className="rounded-2xl bg-[#14141c] border border-white/10 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Score exact (top 5)</h2>
          <div className="flex flex-wrap gap-3">
            {result.exact_scores.map((s, i) => (
              <span key={i} className="rounded-lg bg-dark-input px-3 py-2 text-sm">
                {s.home}-{s.away} <span className="text-[#00ffe8]">{s.probability}%</span>
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Scenarios #2 to #4 */}
      {(result.scenario_2?.title || result.scenario_3?.title || result.scenario_4?.title) && (
        <section className="rounded-2xl bg-[#14141c] border border-white/10 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">💡 Scenarios #2 to #4</h2>
          <div className="space-y-4">
            {[result.scenario_2, result.scenario_3, result.scenario_4].map((s, i) => {
              if (!s?.title && !s?.body) return null;
              return (
                <div key={i} className="rounded-xl bg-dark-input/60 border border-dark-border p-4">
                  <p className="font-semibold text-[#00ffe8] mb-1">{s.title}</p>
                  <p className="text-zinc-300 text-sm leading-relaxed">{s.body}</p>
                  {s.probability_pct != null && (
                    <p className="text-zinc-500 text-xs mt-2">AI analysis gives {s.probability_pct}% probability.</p>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Key forces identified by AI */}
      {((result.key_forces_home && result.key_forces_home.length > 0) || (result.key_forces_away && result.key_forces_away.length > 0)) && (
        <section className="rounded-2xl bg-[#14141c] border border-white/10 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">📰 Key forces identified by AI</h2>
          <div className="grid gap-6 sm:grid-cols-2">
            {result.key_forces_home && result.key_forces_home.length > 0 && (
              <div>
                <p className="font-semibold mb-2 text-white">{home}</p>
                <ul className="space-y-1.5 text-sm text-zinc-300">
                  {result.key_forces_home.map((item, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-[#00ffe8] mt-0.5">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {result.key_forces_away && result.key_forces_away.length > 0 && (
              <div>
                <p className="font-semibold mb-2 text-white">{away}</p>
                <ul className="space-y-1.5 text-sm text-zinc-300">
                  {result.key_forces_away.map((item, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-[#ef4444] mt-0.5">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>
      )}

      <p className="text-center text-zinc-500 text-xs">This analysis is provided for informational purposes only.</p>
    </div>
  );
}
