"use client";

import { useState } from "react";
import Link from "next/link";
import { useLanguage } from "@/contexts/LanguageContext";
import { UnlockFullAnalysisModal } from "@/components/UnlockFullAnalysisModal";
import { UnlockPricingModal } from "@/components/UnlockPricingModal";

type OverUnderItem = { line: string; over_pct: number; under_pct: number };
type ExactScoreItem = { home: number; away: number; probability: number };

type Result = {
  home_team?: string;
  away_team?: string;
  league?: string | null;
  match_date?: string | null;
  /** ISO UTC (ex. 2025-03-15T20:00:00+00:00) pour le countdown "starts in" */
  match_date_iso?: string | null;
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
  internal_prob_home?: number;
  internal_prob_draw?: number;
  internal_prob_away?: number;
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
  /** Full 8-section professional analysis (Sportmonks) */
  professional_analysis?: string | null;
  ai_confidence?: string | null;
  /** News-style context (position, stakes); shown at top with quick_summary */
  match_context_summary?: string | null;
  home_motivation_score?: number;
  away_motivation_score?: number;
  home_motivation_label?: string | null;
  away_motivation_label?: string | null;
  attack_home_pct?: number;
  defense_home_pct?: number;
  form_home_pct?: number;
  h2h_home_pct?: number;
  goals_home_pct?: number;
  overall_home_pct?: number;
  match_over?: boolean;
  final_score_home?: number;
  final_score_away?: number;
  match_statistics?: { type: string; home_value: string | number; away_value: string | number }[];
  full_analysis?: boolean;
  analysis_recap?: {
    data_source?: string;
    form?: {
      home_matches_used?: number;
      away_matches_used?: number;
      home_goals_for_avg?: number;
      home_goals_against_avg?: number;
      away_goals_for_avg?: number;
      away_goals_against_avg?: number;
      home_wdl?: string;
      away_wdl?: string;
    };
    h2h?: {
      matches_count?: number;
      home_wins?: number;
      draws?: number;
      away_wins?: number;
      seasons_used?: number | null;
      raw_matches_count?: number;
      raw_home_wins?: number;
      raw_draws?: number;
      raw_away_wins?: number;
      season_breakdown?: Array<{
        season?: string;
        weight?: number;
        raw_home_wins?: number;
        raw_draws?: number;
        raw_away_wins?: number;
        weighted_home_wins?: number;
        weighted_draws?: number;
        weighted_away_wins?: number;
      }>;
      weighting?: number[];
    };
    probabilities?: {
      model?: string;
      lambda_home?: number;
      lambda_away?: number;
      xg_home?: number;
      xg_away?: number;
      sportmonks_unavailable_reason?: string | null;
    };
    match_info?: {
      fixture_id?: number | null;
      has_upcoming_match?: boolean;
      league?: string | null;
      venue?: string | null;
    };
    motivation?: {
      match_context_summary?: string | null;
      home_motivation_score?: number;
      away_motivation_score?: number;
      home_motivation_label?: string | null;
      away_motivation_label?: string | null;
    };
    ai_summary?: {
      news_included?: boolean;
      context_used?: string;
    };
    api_requests_estimate?: string | null;
    pipeline_steps?: { order: number; title_key: string; detail: string }[];
    stats_period?: string;
    how_bars_work?: Record<string, string>;
    how_score_prediction_works?: string;
    raw_data?: {
      home_goals_for_last5?: number[];
      home_goals_against_last5?: number[];
      away_goals_for_last5?: number[];
      away_goals_against_last5?: number[];
      home_form_last5?: string[];
      away_form_last5?: string[];
      averages?: Record<string, number | undefined>;
      lambdas?: Record<string, number | undefined>;
      comparison_pcts?: Record<string, number | undefined>;
      h2h?: Record<string, number | undefined>;
    };
    scraped_news_count?: number;
    motivation_analysis_used?: boolean;
  } | null;
  scraped_news_count?: number;
  motivation_analysis?: string | null;
  [k: string]: unknown;
};

/** Grand indicateur de forme (Great = flamme orange, Poor = graph violet/rose, Average = barres) */
function FormLabelBlock({ label, compact }: { label: string; compact?: boolean }) {
  const l = (label || "").toLowerCase();
  const isGreat = l.includes("great") || l.includes("bonne") || l.includes("excellent");
  const isPoor = l.includes("poor") || l.includes("faible") || l.includes("difficile");
  const isAverage = l.includes("average") || l.includes("moyenne") || l.includes("moyen");
  const emojiClass = compact ? "text-base" : "text-2xl";
  const labelClass = compact ? "text-xs font-medium text-zinc-300" : "font-semibold text-white";
  return (
    <div className={`flex items-center gap-2 ${compact ? "gap-1.5" : "gap-3"}`}>
      {isGreat && (
        <span className={compact ? "text-base" : "text-3xl"} title="Great form">🔥</span>
      )}
      {isPoor && (
        <span className={emojiClass} title="Poor form">📉</span>
      )}
      {isAverage && !isGreat && !isPoor && (
        <span className={emojiClass} title="Average form">📊</span>
      )}
      {!isGreat && !isPoor && !isAverage && <span className={emojiClass}>📊</span>}
      <span className={labelClass}>{label || "—"}</span>
    </div>
  );
}

/** Truncates long text with "Read more" / "Show less". */
function ReadMore({
  text,
  maxChars = 220,
  className = "",
  t,
}: {
  text: string;
  maxChars?: number;
  className?: string;
  t: (key: string) => string;
}) {
  const [expanded, setExpanded] = useState(false);
  const needsTruncation = text.length > maxChars;
  const display = !needsTruncation || expanded ? text : text.slice(0, maxChars).trim() + (text.length > maxChars ? "…" : "");
  return (
    <div className={className}>
      <p className="text-zinc-300 leading-relaxed text-sm whitespace-pre-line">{display}</p>
      {needsTruncation && (
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="mt-1.5 text-sm font-medium text-[#00ffe8] hover:underline"
        >
          {expanded ? t("analysis.show_less") : t("analysis.readMore")}
        </button>
      )}
    </div>
  );
}

const formIconSize = "w-4 h-4 sm:w-5 sm:h-5";
function AppleCheck() {
  return (
    <span className={`inline-flex items-center justify-center ${formIconSize} flex-shrink-0`} title="Victoire" aria-hidden>✅</span>
  );
}

function AppleCross() {
  return (
    <span className={`inline-flex items-center justify-center ${formIconSize} flex-shrink-0`} title="Défaite" aria-hidden>❌</span>
  );
}

function AppleDraw() {
  return (
    <span className={`inline-flex items-center justify-center ${formIconSize} flex-shrink-0`} title="Nul" aria-hidden>➖</span>
  );
}

function FormIcon({ result }: { result: string }) {
  if (result === "W") return <AppleCheck />;
  if (result === "D") return <AppleDraw />;
  if (result === "L") return <AppleCross />;
  return <span className={`inline-flex ${formIconSize} items-center justify-center rounded border border-zinc-500/50 text-zinc-500 text-xs flex-shrink-0`} title="À venir">?</span>;
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

function PredictionMarketBar({
  leftPct,
  leftLabel,
  rightLabel,
  leftColor = "#22c5ba",
  rightColor = "#f97373",
}: {
  leftPct: number;
  leftLabel: string;
  rightLabel: string;
  leftColor?: string;
  rightColor?: string;
}) {
  const pct = Math.min(100, Math.max(0, leftPct));
  const rightPct = Math.max(0, 100 - pct);
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-sm">
        <span className="text-zinc-300">{leftLabel}</span>
        <span className="text-zinc-300">{rightLabel}</span>
      </div>
      <div className="h-3 bg-[#1c1c28] rounded-full overflow-hidden flex shadow-inner">
        <div
          className="h-full rounded-l-full transition-all duration-300"
          style={{ width: `${pct}%`, backgroundColor: leftColor }}
        />
        <div
          className="h-full flex-1 rounded-r-full opacity-80"
          style={{ backgroundColor: rightColor }}
        />
      </div>
      <div className="flex justify-between text-xs font-medium tabular-nums">
        <span style={{ color: leftColor }}>{pct.toFixed(1)}%</span>
        <span style={{ color: rightColor }}>{rightPct.toFixed(1)}%</span>
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
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const STAT_TYPE_TO_KEY: Record<string, string> = {
  "Ball Possession": "matchOver.stat.possession",
  "Possession": "matchOver.stat.possession",
  "Total Shots": "matchOver.stat.totalShots",
  "Shots on Goal": "matchOver.stat.shotsOnTarget",
  "Shots on target": "matchOver.stat.shotsOnTarget",
  "Shots off Goal": "matchOver.stat.shotsOffTarget",
  "Shots off target": "matchOver.stat.shotsOffTarget",
  "Corner Kicks": "matchOver.stat.corners",
  "Corners": "matchOver.stat.corners",
  "Offsides": "matchOver.stat.offsides",
  "Fouls": "matchOver.stat.fouls",
  "Yellow Cards": "matchOver.stat.yellowCards",
  "Passes %": "matchOver.stat.passAccuracy",
  "Pass accuracy": "matchOver.stat.passAccuracy",
};

function statLabelFromType(type: string, t: (key: string) => string): string {
  const key = STAT_TYPE_TO_KEY[type] ?? STAT_TYPE_TO_KEY[type.trim()];
  return key ? t(key) : type;
}

function statIconFromType(type: string) {
  const t = (type || "").toLowerCase();
  if (t.includes("possession")) return <span className="text-base">⚽</span>;
  if (t.includes("shot") || t.includes("goal")) return <span className="text-base">🎯</span>;
  if (t.includes("corner")) return <span className="text-base">🚩</span>;
  if (t.includes("offside")) return <span className="text-base">⛔</span>;
  if (t.includes("foul")) return <span className="text-base">⚠️</span>;
  if (t.includes("yellow")) return <span className="text-base">🟨</span>;
  if (t.includes("pass")) return <span className="text-base">📊</span>;
  return <span className="text-base">📈</span>;
}

export function AnalysisResult({ result }: { result: Result }) {
  const home = result.home_team ?? "Home";
  const away = result.away_team ?? "Away";
  const { t } = useLanguage();
  const fullAnalysis = result.full_analysis !== false;
  const comparisonSourceLabel = "Custom";
  const [showUnlockModal1, setShowUnlockModal1] = useState(false);
  const [showUnlockModal2, setShowUnlockModal2] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [feedbackStatus, setFeedbackStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  const openUnlockStep1 = () => setShowUnlockModal1(true);
  const closeUnlockStep1 = () => setShowUnlockModal1(false);
  const openUnlockStep2 = () => {
    setShowUnlockModal1(false);
    setShowUnlockModal2(true);
  };
  const closeUnlockStep2 = () => setShowUnlockModal2(false);

  const sendFeedback = async () => {
    const msg = feedback.trim();
    if (msg.length < 4 || feedbackStatus === "sending") return;
    setFeedbackStatus("sending");
    try {
      let uid = "";
      if (typeof window !== "undefined") {
        uid = localStorage.getItem("visifoot_uid") || "";
      }
      const res = await fetch(`${API_URL}/internal/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: msg,
          user_id: uid || null,
          home_team: result.home_team ?? null,
          away_team: result.away_team ?? null,
          page: "analysis",
        }),
      });
      if (!res.ok) throw new Error("feedback_failed");
      setFeedback("");
      setFeedbackStatus("sent");
      setTimeout(() => setFeedbackStatus("idle"), 3000);
    } catch {
      setFeedbackStatus("error");
    }
  };

  const summaryText = (() => {
    const raw = String(result.quick_summary ?? "").trim();
    if (!raw) return "";
    if (fullAnalysis) return raw;
    const cleaned = raw
      .split("\n")
      .filter((line) => {
        const l = line.toLowerCase();
        if (line.includes("%")) return false;
        return !/(xg|probab|1x2|odds|over\/under|btts)/.test(l);
      })
      .join("\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
    const newsCount =
      (typeof result.scraped_news_count === "number" ? result.scraped_news_count : undefined) ??
      (typeof result.analysis_recap?.scraped_news_count === "number" ? result.analysis_recap.scraped_news_count : 0);
    const credibilityLine =
      newsCount > 0
        ? `Credibility boost: cross-checked with ${newsCount} recent news/commentary signals.`
        : "Credibility boost: cross-checked with recent football news and live commentary signals.";
    return [cleaned, credibilityLine].filter(Boolean).join("\n\n");
  })();

  const blurWrap = (content: React.ReactNode) => {
    if (fullAnalysis) return content;
    return (
      <div className="relative">
        <div className="select-none pointer-events-none blur-md opacity-90" aria-hidden>
          {content}
        </div>
        <UnlockPricingModal open={showUnlockModal2} onClose={closeUnlockStep2} />
      </div>
    );
  };

  /** Overlay 15% + CTA — positionné bien en bas du flou pour ne pas chevaucher Exact statistics */
  const exactProbabilitiesOverlay = () => (
    <div className="absolute inset-0 z-10 flex flex-col justify-end items-center p-4 pb-6 pt-24 sm:pt-32">
      <div className="rounded-2xl bg-[#14141c]/95 border-2 border-[#00ffe8]/30 p-5 sm:p-6 max-w-md w-full shadow-xl text-center relative z-10">
        <h3 className="text-lg sm:text-xl font-bold text-white">
          {t("analysis.limitedAccessTitle")}
        </h3>
        <div className="w-full max-w-xs h-2.5 bg-zinc-700 rounded-full mt-4 mx-auto overflow-hidden flex">
          <div className="h-full bg-[#00ffe8] rounded-l-full transition-all duration-500" style={{ width: "15%" }} />
          <div className="h-full flex-1 bg-zinc-600 rounded-r-full" />
        </div>
        <p className="text-zinc-300 text-sm mt-4">
          {t("analysis.limitedAccessDesc")}
        </p>
        <button
          type="button"
          onClick={openUnlockStep1}
          className="mt-6 w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-semibold text-[#0d0d12] bg-[#00ffe8] hover:bg-[#00ffe8]/90 transition relative z-20"
        >
          <span className="text-lg" aria-hidden>🏆</span>
          {t("analysis.unlockFullAnalysis")}
        </button>
      </div>
    </div>
  );

  return (
    <div className="rounded-2xl bg-[#14141c] border border-white/10 overflow-visible shadow-lg relative">
      <div className="p-4 sm:p-6 space-y-0">
      {/* AI analysis ready — mobile: tout en haut centré, dépasse pour rester visible (pas coupé); desktop: haut droite */}
      <div className="absolute -top-2 left-1/2 -translate-x-1/2 sm:left-auto sm:right-3 sm:top-3 sm:translate-x-0 z-20">
        <div className="rounded-md border border-[#00ffe8]/50 bg-[#0a0a0e]/95 px-2 py-1 text-center shadow-lg">
          <p className="text-[#00ffe8] font-medium text-[10px] sm:text-xs leading-tight">{t("analysis.aiReady")}</p>
          <p className="text-[#00ffe8]/70 text-[9px] sm:text-[10px] leading-tight">{t("analysis.basedOn")}</p>
        </div>
      </div>
      {/* Recap - first section: mobile = logos above, names + VS on new lines; desktop = logo | text | logo */}
      <div className="pb-4 sm:pb-6 pt-4 sm:pt-0">
        <div className="flex flex-wrap items-center justify-between gap-4 sm:pr-24">
          <div className="min-w-0 flex-1 flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
            {/* Mobile: logos row then label + home / vs / away on new lines */}
            <div className="flex flex-col items-center sm:hidden">
              <div className="flex items-center justify-center gap-3">
                {result.home_team_logo ? (
                  <img src={result.home_team_logo} alt="" className="w-12 h-12 object-contain flex-shrink-0" />
                ) : (
                  <div className="w-12 h-12 rounded-xl bg-[#1c1c28] flex items-center justify-center text-white font-bold text-sm">{home.slice(0, 2)}</div>
                )}
                {result.away_team_logo ? (
                  <img src={result.away_team_logo} alt="" className="w-12 h-12 object-contain flex-shrink-0" />
                ) : (
                  <div className="w-12 h-12 rounded-xl bg-[#1c1c28] flex items-center justify-center text-white font-bold text-sm">{away.slice(0, 2)}</div>
                )}
              </div>
              <p className="text-zinc-500 text-xs sm:text-sm mt-1.5">{t("analysis.analyzedMatch")}</p>
              <h1 className="text-lg sm:text-xl font-bold mt-0.5 text-white text-center">
                <span className="text-white block">{home}</span>
                <span className="text-zinc-500 font-normal block my-0.5">vs</span>
                <span className="text-white block">{away}</span>
              </h1>
            </div>
            {/* Desktop: logo | text | logo */}
            <div className="hidden sm:flex items-center gap-4 min-w-0 flex-1">
              {result.home_team_logo ? (
                <img src={result.home_team_logo} alt="" className="w-14 h-14 object-contain flex-shrink-0" />
              ) : (
                <div className="w-14 h-14 rounded-xl bg-[#1c1c28] flex-shrink-0 flex items-center justify-center text-white font-bold">{home.slice(0, 2)}</div>
              )}
              <div className="min-w-0">
                <p className="text-zinc-500 text-xs sm:text-sm">{t("analysis.analyzedMatch")}</p>
                <h1 className="text-lg sm:text-xl md:text-2xl font-bold mt-0.5 text-white">
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
          </div>
        </div>
        {(result.league || result.match_date || result.venue) && (
          <div className="mt-3 sm:mt-5 pt-3 sm:pt-4 border-t border-white/10 flex flex-wrap gap-x-4 sm:gap-x-6 gap-y-1 text-xs sm:text-sm text-white">
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

      {/* Match terminé : bandeau teal + score final + stats */}
      {result.match_over && result.final_score_home != null && result.final_score_away != null && (
        <>
          <div className="mt-6 pt-6 border-t border-white/5 rounded-xl bg-[#0d4d47] border border-[#22c5ba]/30 p-5 text-white">
            <p className="text-sm leading-relaxed">
              {t("matchOver.banner")
                .replace("{home}", home)
                .replace("{away}", away)}
            </p>
          </div>
          <section className="pt-6 border-t border-white/5">
            <h2 className="text-lg font-semibold text-white text-center mb-6">{t("matchOver.finalScore")}</h2>
            <div className="flex items-center justify-center gap-6 flex-wrap">
              <div className="flex flex-col items-center gap-2 min-w-[100px]">
                {result.home_team_logo ? (
                  <img src={result.home_team_logo} alt="" className="w-16 h-16 object-contain" />
                ) : (
                  <div className="w-16 h-16 rounded-xl bg-[#1c1c28] flex items-center justify-center text-white font-bold">{home.slice(0, 2)}</div>
                )}
                <span className="text-white font-medium">{home}</span>
              </div>
              <div className="flex flex-col items-center gap-0.5">
                <span className="text-zinc-500 text-sm">–</span>
                <div className="flex items-baseline gap-2">
                  <span className={`text-3xl font-bold ${HOME_COLOR}`}>{result.final_score_home}</span>
                  <span className="text-zinc-500 text-xl">-</span>
                  <span className={`text-3xl font-bold ${AWAY_COLOR}`}>{result.final_score_away}</span>
                </div>
              </div>
              <div className="flex flex-col items-center gap-2 min-w-[100px]">
                {result.away_team_logo ? (
                  <img src={result.away_team_logo} alt="" className="w-16 h-16 object-contain" />
                ) : (
                  <div className="w-16 h-16 rounded-xl bg-[#1c1c28] flex items-center justify-center text-white font-bold">{away.slice(0, 2)}</div>
                )}
                <span className="text-white font-medium">{away}</span>
              </div>
            </div>
          </section>
          {/* Match statistics title only when match over — content is inside blur below for free plan */}
          {result.match_statistics && result.match_statistics.length > 0 && fullAnalysis && (
            <section className="pt-6 border-t border-white/5">
              <h2 className="text-lg font-semibold text-white mb-5 flex items-center gap-2">
                <span className="text-zinc-400">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </span>
                {t("matchOver.matchStatistics")}
              </h2>
              <div className="space-y-5">
                {result.match_statistics.map((stat, idx) => {
                  const label = statLabelFromType(stat.type, t);
                  const homeVal = stat.home_value;
                  const awayVal = stat.away_value;
                  const homeNum = typeof homeVal === "string" ? parseFloat(String(homeVal).replace("%", "")) : Number(homeVal);
                  const awayNum = typeof awayVal === "string" ? parseFloat(String(awayVal).replace("%", "")) : Number(awayVal);
                  const total = homeNum + awayNum;
                  const homePct = total > 0 ? (homeNum / total) * 100 : 50;
                  const isPct = typeof homeVal === "string" && String(homeVal).includes("%");
                  const homeDisplay = isPct ? `${homeNum}%` : String(homeVal);
                  const awayDisplay = isPct ? `${awayNum}%` : String(awayVal);
                  return (
                    <div key={idx} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-zinc-400 flex items-center gap-2">
                          {statIconFromType(stat.type)}
                          {label}
                        </span>
                        <span className="flex gap-4 tabular-nums">
                          <span className={HOME_COLOR}>{homeDisplay}</span>
                          <span className={AWAY_COLOR}>{awayDisplay}</span>
                        </span>
                      </div>
                      <div className="h-3 bg-[#1c1c28] rounded-full overflow-hidden flex">
                        <div className="h-full rounded-l-full transition-all" style={{ width: `${Math.min(100, Math.max(0, homePct))}%`, background: HOME_HEX }} />
                        <div className="h-full flex-1 rounded-r-full opacity-80" style={{ background: AWAY_HEX }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}
        </>
      )}

      {/* Recent form — compact single block */}
      <section className="pt-4 sm:pt-6 border-t border-white/5">
        <div className="rounded-xl bg-[#1c1c28] border border-white/5 p-3 sm:p-4">
          <div className="flex flex-wrap items-center justify-between gap-1.5 sm:gap-2 mb-2 sm:mb-3">
            <h2 className="text-sm sm:text-base font-semibold text-white flex items-center gap-1.5 sm:gap-2">
              <span className="text-zinc-400 text-xs sm:text-base">📊</span> {t("analysis.recentForm")}
            </h2>
            <span className="text-zinc-500 text-[10px] sm:text-xs">{t("analysis.globalForm")}</span>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:gap-4">
            <div className="flex items-center gap-2 sm:gap-3 min-w-0">
              {result.home_team_logo ? (
                <img src={result.home_team_logo} alt="" className="w-8 h-8 sm:w-9 sm:h-9 object-contain flex-shrink-0" />
              ) : (
                <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-dark-input flex-shrink-0 flex items-center justify-center text-white font-bold text-[10px] sm:text-xs">{home.slice(0, 2)}</div>
              )}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1 sm:gap-2 flex-wrap">
                  <p className="font-semibold text-white text-xs sm:text-sm truncate">{home}</p>
                  <FormLabelBlock label={result.home_form_label ?? ""} compact />
                </div>
                <p className="text-[10px] sm:text-xs text-zinc-400 mt-0.5 sm:mt-1 flex items-center gap-0.5 sm:gap-1.5 flex-wrap">
                  {(() => {
                    const form5 = [...(result.home_form ?? []).slice(0, 5)];
                    while (form5.length < 5) form5.push("");
                    return form5.map((r, i) => <FormIcon key={i} result={r} />);
                  })()}
                  <span className="text-zinc-500">W-D-L: {result.home_wdl ?? "—"}</span>
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 sm:gap-3 min-w-0">
              {result.away_team_logo ? (
                <img src={result.away_team_logo} alt="" className="w-8 h-8 sm:w-9 sm:h-9 object-contain flex-shrink-0" />
              ) : (
                <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-dark-input flex-shrink-0 flex items-center justify-center text-white font-bold text-[10px] sm:text-xs">{away.slice(0, 2)}</div>
              )}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1 sm:gap-2 flex-wrap">
                  <p className="font-semibold text-white text-xs sm:text-sm truncate">{away}</p>
                  <FormLabelBlock label={result.away_form_label ?? ""} compact />
                </div>
                <p className="text-[10px] sm:text-xs text-zinc-400 mt-0.5 sm:mt-1 flex items-center gap-0.5 sm:gap-1.5 flex-wrap">
                  {(() => {
                    const form5 = [...(result.away_form ?? []).slice(0, 5)];
                    while (form5.length < 5) form5.push("");
                    return form5.map((r, i) => <FormIcon key={i} result={r} />);
                  })()}
                  <span className="text-zinc-500">W-D-L: {result.away_wdl ?? "—"}</span>
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Quick summary - visible for free plan (includes match context / news at top) */}
      {summaryText && (
        <section className="pt-4 sm:pt-6 border-t border-white/5">
          <h2 className="text-sm sm:text-base font-semibold text-white mb-2 sm:mb-3 flex items-center gap-1.5 sm:gap-2">
            <span className="text-[#00ffe8] text-xs sm:text-base">🔍</span> {t("analysis.summary")}
          </h2>
          <ReadMore text={summaryText} maxChars={220} t={t} />
          <p className="text-[10px] sm:text-xs text-[#00ffe8] mt-1.5 sm:mt-2">Generated from millions of data points and football news.</p>
        </section>
      )}

      {/* Match Importance - motivation scores (Sportmonks standings-based) */}
      {(result.home_motivation_label || result.away_motivation_label) && (
        <section className="pt-4 sm:pt-6 border-t border-white/5">
          <h2 className="text-sm sm:text-base font-semibold text-white mb-2 sm:mb-3 flex items-center gap-1.5 sm:gap-2">
            <span className="text-[#00ffe8] text-xs sm:text-base">⚔️</span> {t("analysis.matchImportance")}
          </h2>
          <div className="rounded-xl bg-[#1c1c28] border border-white/5 p-2.5 sm:p-4 flex flex-wrap gap-2 sm:gap-4">
            <div className="flex items-center gap-1.5 sm:gap-2">
              <span className="text-zinc-400 text-xs sm:text-sm">{result.home_team}</span>
              <span className="text-white font-medium text-xs sm:text-base capitalize">{result.home_motivation_label || "—"}</span>
            </div>
            <div className="flex items-center gap-1.5 sm:gap-2">
              <span className="text-zinc-400 text-xs sm:text-sm">{result.away_team}</span>
              <span className="text-white font-medium text-xs sm:text-base capitalize">{result.away_motivation_label || "—"}</span>
            </div>
          </div>
        </section>
      )}

      {/* Scenario #1 - visible for free plan */}
      {result.scenario_1 && (
        <section className="pt-4 sm:pt-6 border-t border-white/5">
          <h2 className="text-sm sm:text-base font-semibold text-white mb-2 sm:mb-3 flex items-center gap-1.5 sm:gap-2">
            <span className="text-xs sm:text-base">📌</span> {t("analysis.scenario")} #1
          </h2>
          <ReadMore text={result.scenario_1} maxChars={220} t={t} />
        </section>
      )}

      {/* AI confidence — visible for free plan, blur starts after this */}
      {result.ai_confidence && (() => {
        const label = String(result.ai_confidence).trim();
        const confLower = label.toLowerCase();
        const pct = confLower.includes("very high") || confLower.includes("très élevé") ? 92
          : confLower.includes("high") || confLower.includes("élevé") ? 75
          : confLower.includes("medium") || confLower.includes("moyen") ? 50
          : confLower.includes("low") || confLower.includes("faible") ? 28
          : 60;
        return (
          <section className="pt-6 border-t border-white/5">
            <div className="rounded-xl bg-[#1c1c28] border border-white/5 p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-zinc-400 text-sm font-medium">🧠 AI confidence</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 min-w-0 h-2 bg-dark-input rounded-full overflow-hidden">
                  <div className="h-full bg-[#00ffe8] rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
                </div>
                <span className="text-zinc-300 text-sm font-medium whitespace-nowrap flex-shrink-0">{label}</span>
              </div>
              <p className="text-zinc-500 text-xs mt-1.5">Confidence level based on available data quality.</p>
            </div>
          </section>
        );
      })()}

      {/* From here: blurred for free plan — match stats (when match over), then Model win probabilities has its own title + blur+overlay */}
      {blurWrap(
        <>
      {/* Match statistics content (when match over) */}
      {result.match_over && result.match_statistics && result.match_statistics.length > 0 && (
        <section className="pt-6 border-t border-white/5">
          <div className="space-y-5">
            {result.match_statistics.map((stat, idx) => {
              const label = statLabelFromType(stat.type, t);
              const homeVal = stat.home_value;
              const awayVal = stat.away_value;
              const homeNum = typeof homeVal === "string" ? parseFloat(String(homeVal).replace("%", "")) : Number(homeVal);
              const awayNum = typeof awayVal === "string" ? parseFloat(String(awayVal).replace("%", "")) : Number(awayVal);
              const total = homeNum + awayNum;
              const homePct = total > 0 ? (homeNum / total) * 100 : 50;
              const isPct = typeof homeVal === "string" && String(homeVal).includes("%");
              const homeDisplay = isPct ? `${homeNum}%` : String(homeVal);
              const awayDisplay = isPct ? `${awayNum}%` : String(awayVal);
              return (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-zinc-400 flex items-center gap-2">
                      {statIconFromType(stat.type)}
                      {label}
                    </span>
                    <span className="flex gap-4 tabular-nums">
                      <span className={HOME_COLOR}>{homeDisplay}</span>
                      <span className={AWAY_COLOR}>{awayDisplay}</span>
                    </span>
                  </div>
                  <div className="h-3 bg-[#1c1c28] rounded-full overflow-hidden flex">
                    <div className="h-full rounded-l-full transition-all" style={{ width: `${Math.min(100, Math.max(0, homePct))}%`, background: HOME_HEX }} />
                    <div className="h-full flex-1 rounded-r-full opacity-80" style={{ background: AWAY_HEX }} />
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}
        </>
      )}

      {/* Model win probabilities — Poisson + motivation + recent performance blend */}
      <section className="pt-6 border-t border-white/5">
        <h2 className="text-lg font-semibold text-white mb-4">📊 {t("analysis.exactStatistics")}</h2>
        {fullAnalysis ? (
          <>
            <div className="space-y-3 mb-4">
              <div className="flex items-center gap-2">
                <span className="text-zinc-300 text-sm w-20 flex-shrink-0">{home} win</span>
                <div className="flex-1 min-w-0 h-2 bg-dark-input rounded-full overflow-hidden">
                  <div className="h-full bg-[#00ffe8] rounded-full transition-all duration-500" style={{ width: `${result.internal_prob_home ?? result.prob_home ?? 0}%` }} />
                </div>
                <span className="text-[#00ffe8] font-semibold text-sm w-9 text-right flex-shrink-0 tabular-nums">{result.internal_prob_home ?? result.prob_home ?? 0}%</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-zinc-300 text-sm w-20 flex-shrink-0">Draw</span>
                <div className="flex-1 min-w-0 h-2 bg-dark-input rounded-full overflow-hidden">
                  <div className="h-full bg-[#a3a3a3] rounded-full transition-all duration-500" style={{ width: `${result.internal_prob_draw ?? result.prob_draw ?? 0}%` }} />
                </div>
                <span className="text-zinc-300 font-semibold text-sm w-9 text-right flex-shrink-0 tabular-nums">{result.internal_prob_draw ?? result.prob_draw ?? 0}%</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-zinc-300 text-sm w-20 flex-shrink-0">{away} win</span>
                <div className="flex-1 min-w-0 h-2 bg-dark-input rounded-full overflow-hidden">
                  <div className="h-full bg-[#ef4444] rounded-full transition-all duration-500" style={{ width: `${result.internal_prob_away ?? result.prob_away ?? 0}%` }} />
                </div>
                <span className="text-[#ef4444] font-semibold text-sm w-9 text-right flex-shrink-0 tabular-nums">{result.internal_prob_away ?? result.prob_away ?? 0}%</span>
              </div>
            </div>
            {result.implied_odds_home != null && (
              <>
                <p className="text-zinc-500 text-xs mb-2 mt-3">{t("betting.impliedOdds")} (decimal, compare with bookmakers)</p>
                <div className="flex flex-wrap gap-4 text-xs text-zinc-500">
                  <span>{home} ~{result.implied_odds_home}</span>
                  <span>Draw ~{result.implied_odds_draw ?? "—"}</span>
                  <span>{away} ~{result.implied_odds_away ?? "—"}</span>
                </div>
              </>
            )}
          </>
        ) : (
          <div className="relative min-h-[320px]">
            <div className="select-none pointer-events-none blur-sm opacity-85 absolute inset-0" aria-hidden>
              <div className="space-y-3 mb-4">
                <div className="flex items-center gap-2">
                  <span className="text-zinc-300 text-sm w-20 flex-shrink-0">{home} win</span>
                  <div className="flex-1 min-w-0 h-2 bg-dark-input rounded-full overflow-hidden">
                    <div className="h-full bg-[#00ffe8] rounded-full" style={{ width: `${result.internal_prob_home ?? result.prob_home ?? 0}%` }} />
                  </div>
                  <span className="text-[#00ffe8] font-semibold text-sm w-9 text-right flex-shrink-0 tabular-nums">{result.internal_prob_home ?? result.prob_home ?? 0}%</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-zinc-300 text-sm w-20 flex-shrink-0">Draw</span>
                  <div className="flex-1 min-w-0 h-2 bg-dark-input rounded-full overflow-hidden">
                    <div className="h-full bg-[#00ffe8] rounded-full" style={{ width: `${result.internal_prob_draw ?? result.prob_draw ?? 0}%` }} />
                  </div>
                  <span className="text-zinc-300 font-semibold text-sm w-9 text-right flex-shrink-0 tabular-nums">{result.internal_prob_draw ?? result.prob_draw ?? 0}%</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-zinc-300 text-sm w-20 flex-shrink-0">{away} win</span>
                  <div className="flex-1 min-w-0 h-2 bg-dark-input rounded-full overflow-hidden">
                    <div className="h-full bg-[#00ffe8] rounded-full" style={{ width: `${result.internal_prob_away ?? result.prob_away ?? 0}%` }} />
                  </div>
                  <span className="text-[#ef4444] font-semibold text-sm w-9 text-right flex-shrink-0 tabular-nums">{result.internal_prob_away ?? result.prob_away ?? 0}%</span>
                </div>
              </div>
              {result.implied_odds_home != null && (
                <p className="text-zinc-500 text-xs">Implied odds (decimal)</p>
              )}
            </div>
            {exactProbabilitiesOverlay()}
          </div>
        )}
      </section>
      <UnlockFullAnalysisModal
        open={showUnlockModal1}
        onClose={closeUnlockStep1}
        onUnlockClick={openUnlockStep2}
        matchLabel={home && away ? `${home} vs ${away}` : undefined}
        matchDate={(result.match_date_iso ?? result.match_date) ?? undefined}
      />
      <UnlockPricingModal open={showUnlockModal2} onClose={closeUnlockStep2} />

      {/* Reste de l'analyse (flouté pour free) */}
      {blurWrap(
        <>
      {/* Scenarios #2 to #4 — after Model win probabilities */}
      {(result.scenario_2?.title || result.scenario_3?.title || result.scenario_4?.title) && (
        <section className="pt-6 border-t border-white/5">
          <h2 className="text-lg font-semibold text-white mb-4">💡 Scenarios #2 to #4</h2>
          <div className="space-y-4">
            {[result.scenario_2, result.scenario_3, result.scenario_4].map((s, i) => {
              if (!s?.title && !s?.body) return null;
              const body = (s.body ?? "").trim();
              return (
                <div key={i} className="rounded-xl bg-dark-input/60 border border-dark-border p-4">
                  <p className="font-semibold text-[#00ffe8] mb-1">{s.title}</p>
                  {body ? <ReadMore text={body} maxChars={220} t={t} /> : null}
                  {s.probability_pct != null && (
                    <p className="text-zinc-500 text-xs mt-2">AI analysis gives {s.probability_pct}% probability.</p>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Score le plus probable + 2e à 5e en petit + distribution buts + écart */}
      {(result.most_likely_score || result.total_goals_distribution || result.goal_difference_dist) && (
        <section className="pt-6 border-t border-white/5">
          <h2 className="text-lg font-semibold text-white mb-4">🎯 {t("betting.mostLikelyScore")} & distributions</h2>
          {result.most_likely_score && (
            <div className="mb-4 flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <div>
                <p className="text-zinc-400 text-sm mb-1">{t("betting.mostLikelyScore")}</p>
                <p className="text-xl font-bold text-white">{result.most_likely_score.home}-{result.most_likely_score.away} <span className="text-[#00ffe8]">({result.most_likely_score.probability}%)</span></p>
                <p className="text-zinc-500 text-xs mt-1">{t("analysis.expectedGoals")} (xG): {result.xg_home ?? 0} – {result.xg_away ?? 0}</p>
              </div>
              {result.exact_scores && result.exact_scores.length > 1 && (
                <p className="text-zinc-400 text-xs mt-1">
                  {result.exact_scores.slice(1, 5).map((s, i) => (
                    <span key={i}>
                      {i > 0 && " · "}
                      {i + 2}e: <span className="text-white">{s.home}-{s.away}</span> <span className="text-[#00ffe8]">{s.probability}%</span>
                    </span>
                  ))}
                </p>
              )}
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
        <section className="pt-6 border-t border-white/5">
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

      {/* Key forces identified by AI — before Statistical comparison */}
      {((result.key_forces_home && result.key_forces_home.length > 0) || (result.key_forces_away && result.key_forces_away.length > 0)) && (
        <section className="pt-6 border-t border-white/5">
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

      {/* Recent performance comparison - barres forme/buts/H2H (pas les probas du modèle) */}
      <section className="pt-6 border-t border-white/5">
        <h2 className="text-lg font-semibold text-white mb-2">📊 {t("analysis.recentPerformanceComparison")}</h2>
        <p className="text-zinc-500 text-xs mb-3">{t("analysis.statsSource").replace("{source}", comparisonSourceLabel)}</p>
        <div className="flex justify-between text-sm font-semibold mb-3 px-1">
          <span className={HOME_COLOR}>{home}</span>
          <span className={AWAY_COLOR}>{away}</span>
        </div>
        <div className="space-y-5">
          <StatBar label="Attack" homePct={result.attack_home_pct} homeColor={HOME_COLOR} awayColor={AWAY_COLOR} />
          <StatBar label="Defense" homePct={result.defense_home_pct} homeColor={HOME_COLOR} awayColor={AWAY_COLOR} />
          <StatBar label="Form" homePct={result.form_home_pct} homeColor={HOME_COLOR} awayColor={AWAY_COLOR} />
          <StatBar label={t("analysis.h2hLabel")} homePct={result.h2h_home_pct} homeColor={HOME_COLOR} awayColor={AWAY_COLOR} />
          <StatBar label="Goals" homePct={result.goals_home_pct} homeColor={HOME_COLOR} awayColor={AWAY_COLOR} />
          <StatBar label="Overall" homePct={result.overall_home_pct} homeColor={HOME_COLOR} awayColor={AWAY_COLOR} />
        </div>
      </section>

      {/* Our predictions */}
      <section className="pt-6 border-t border-white/5">
        <h2 className="text-lg font-semibold text-white mb-4">🎯 Our predictions</h2>
        <div className="space-y-4">
          <div className="rounded-2xl bg-white/5 border border-white/10 p-4 sm:p-5">
            <h3 className="text-base font-semibold text-white mb-3">Expected goals</h3>
            <div className="space-y-1 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-zinc-300">{home}</span>
                <span className="font-semibold tabular-nums" style={{ color: HOME_HEX }}>{typeof result.xg_home === "number" ? result.xg_home.toFixed(2) : "0.00"} goals</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-zinc-300">{away}</span>
                <span className="font-semibold tabular-nums" style={{ color: AWAY_HEX }}>{typeof result.xg_away === "number" ? result.xg_away.toFixed(2) : "0.00"} goals</span>
              </div>
              <div className="h-px bg-white/10 my-2" />
              <div className="flex items-center justify-between">
                <span className="text-zinc-400">Total</span>
                <span className="text-white font-semibold tabular-nums">{typeof result.xg_total === "number" ? result.xg_total.toFixed(2) : "0.00"} goals</span>
              </div>
            </div>
            {typeof result.btts_yes_pct === "number" && (
              <div className="mt-5">
                <h4 className="text-base font-semibold text-white mb-2">Both teams to score</h4>
                <PredictionMarketBar
                  leftPct={result.btts_yes_pct}
                  leftLabel="Yes"
                  leftColor={HOME_HEX}
                  rightColor={AWAY_HEX}
                  rightLabel="No"
                />
              </div>
            )}
          </div>

          {result.over_under != null && (() => {
            const GOAL_LINES = ["0.5", "1.5", "2.5", "3.5"];
            const overUnderDisplay = GOAL_LINES.map((line) => {
              const ou = result.over_under?.find((o) => o.line === line);
              return ou ?? { line, over_pct: 50, under_pct: 50 };
            });
            return (
              <div className="rounded-2xl bg-white/5 border border-white/10 p-4 sm:p-5">
                <h3 className="text-base font-semibold text-white mb-3">Goal count probabilities</h3>
                <div className="space-y-4">
                  {overUnderDisplay.map((ou) => (
                    <PredictionMarketBar
                      key={ou.line}
                      leftPct={ou.over_pct}
                      leftLabel={`Over ${ou.line} goals`}
                      rightLabel={`Under ${ou.line} goals`}
                      leftColor={HOME_HEX}
                      rightColor={AWAY_HEX}
                    />
                  ))}
                </div>
              </div>
            );
          })()}
        </div>
      </section>
        </>
      )}

      <section className="pt-6 mt-6 border-t border-white/5">
        <h3 className="text-sm font-semibold text-white mb-2">Help us improve the product</h3>
        <p className="text-zinc-400 text-xs mb-3">
          Want more data or have any feedback on the product? Let us know.
        </p>
        <div className="space-y-2">
          <input
            type="text"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Your feedback..."
            className="w-full rounded-lg bg-dark-input border border-dark-border px-3 py-2 text-sm text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-[#00ffe8]/40"
          />
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={sendFeedback}
              disabled={feedbackStatus === "sending" || feedback.trim().length < 4}
              className="px-4 py-2 rounded-lg bg-[#00ffe8] text-[#0d0d12] text-sm font-semibold disabled:opacity-50"
            >
              {feedbackStatus === "sending" ? "Sending..." : "Send feedback"}
            </button>
            {feedbackStatus === "sent" && <span className="text-xs text-emerald-400">Thanks for your feedback.</span>}
            {feedbackStatus === "error" && <span className="text-xs text-rose-400">Could not send feedback.</span>}
          </div>
        </div>
      </section>

      <p className="text-center text-zinc-500 text-xs pt-6 border-t border-white/5">This analysis is provided for informational purposes only.</p>
      </div>
    </div>
  );
}
