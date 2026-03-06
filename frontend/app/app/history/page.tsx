"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/contexts/LanguageContext";
import { getHistoryKey } from "@/lib/auth";

type HistoryItem = {
  id: string;
  home_team: string;
  away_team: string;
  home_logo?: string | null;
  away_logo?: string | null;
  league?: string | null;
  created_at: string;
  result: Record<string, unknown>;
};

function readString(v: unknown): string | null {
  if (typeof v !== "string") return null;
  const s = v.trim();
  return s ? s : null;
}

function Logo({ src, alt }: { src: string | null; alt: string }) {
  if (!src) {
    return <div className="w-8 h-8 rounded-full bg-dark-input flex-shrink-0" aria-hidden />;
  }
  return <img src={src} alt={alt} className="w-8 h-8 object-contain flex-shrink-0" />;
}

function BarChartEmptyIcon() {
  return (
    <div className="w-16 h-16 rounded-xl bg-white/5 flex items-center justify-center shadow-lg">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" className="flex-shrink-0">
        <rect x="4" y="14" width="4" height="6" rx="1" fill="#ec4899" />
        <rect x="10" y="10" width="4" height="10" rx="1" fill="#3b82f6" />
        <rect x="16" y="6" width="4" height="14" rx="1" fill="#22c55e" />
      </svg>
    </div>
  );
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso.slice(0, 16);
  }
}

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const router = useRouter();
  const { t } = useLanguage();

  useEffect(() => {
    try {
      const key = getHistoryKey();
      const raw = localStorage.getItem(key);
      setItems(raw ? JSON.parse(raw) : []);
    } catch {
      setItems([]);
    }
  }, []);

  const openAnalysis = (item: HistoryItem) => {
    const params = new URLSearchParams({
      team1: item.home_team,
      team2: item.away_team,
      fromHistory: "true",
      predictionId: item.id,
    });
    router.push(`/analyze?${params.toString()}`);
  };

  return (
    <div className="p-4 sm:p-8 w-full flex flex-col items-center">
      <div className="w-full max-w-xl mx-auto">
        <h1 className="text-2xl font-bold text-white">{t("history.title")}</h1>
        <p className="text-zinc-500 mt-1">{t("history.subtitle")}</p>

        {items.length === 0 ? (
          <div className="mt-10 rounded-2xl bg-dark-card border border-dark-border p-12 flex flex-col items-center justify-center text-center shadow-glow">
            <BarChartEmptyIcon />
            <h2 className="text-lg font-semibold text-white mt-6">{t("history.noAnalyses")}</h2>
            <p className="text-zinc-500 mt-2 max-w-sm">
              {t("history.startBy")}
            </p>
            <Link
              href="/matches"
              className="mt-8 px-6 py-4 rounded-xl font-semibold text-black bg-gradient-to-r from-[#00ffe8] to-[#00ddcc] hover:opacity-90 transition shadow-glow"
            >
              {t("history.analyzeMatch")}
            </Link>
          </div>
        ) : (
        <ul className="mt-8 space-y-3">
          {items.map((item) => (
            <li key={item.id}>
              {(() => {
                const r = item.result as Record<string, unknown>;
                const homeLogo = item.home_logo ?? readString(r?.home_team_logo);
                const awayLogo = item.away_logo ?? readString(r?.away_team_logo);
                const league = item.league ?? readString(r?.league);
                return (
              <button
                type="button"
                onClick={() => openAnalysis(item)}
                className="w-full rounded-xl bg-dark-card border border-dark-border p-4 text-left hover:bg-dark-input/60 hover:border-accent-green/40 transition"
              >
                <div className="flex items-center gap-3">
                  <Logo src={homeLogo} alt={item.home_team} />
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-white truncate">
                      {item.home_team} <span className="text-zinc-500 font-normal mx-1">vs</span> {item.away_team}
                    </p>
                    <div className="flex items-center gap-2 flex-wrap mt-1">
                      {league ? (
                        <span className="inline-flex items-center gap-1 text-xs text-zinc-400">
                          <span className="text-amber-300">🏆</span>
                          <span className="truncate max-w-[18rem]">{league}</span>
                        </span>
                      ) : null}
                      <span className="text-zinc-500 text-xs">{formatDate(item.created_at)}</span>
                    </div>
                  </div>
                  <Logo src={awayLogo} alt={item.away_team} />
                </div>
              </button>
                );
              })()}
            </li>
          ))}
        </ul>
        )}
      </div>
    </div>
  );
}
