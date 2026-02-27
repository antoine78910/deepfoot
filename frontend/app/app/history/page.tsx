"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/contexts/LanguageContext";
import { useAppBasePath } from "@/contexts/AppBasePathContext";

const HISTORY_KEY = "visifoot_history";

type HistoryItem = {
  id: string;
  home_team: string;
  away_team: string;
  created_at: string;
  result: Record<string, unknown>;
};

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
  const basePath = useAppBasePath();

  useEffect(() => {
    try {
      const raw = localStorage.getItem(HISTORY_KEY);
      setItems(raw ? JSON.parse(raw) : []);
    } catch {
      setItems([]);
    }
  }, []);

  const openAnalysis = (item: HistoryItem) => {
    sessionStorage.setItem("visifoot_analysis", JSON.stringify(item.result));
    router.push(`${basePath}/analysis`);
  };

  return (
    <div className="p-8 w-full flex flex-col items-center">
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
              href={`${basePath}/matches`}
              className="mt-8 px-6 py-4 rounded-xl font-semibold text-white bg-gradient-to-r from-[#00ffe8] to-[#00ddcc] hover:opacity-90 transition shadow-glow"
            >
              {t("history.analyzeMatch")}
            </Link>
          </div>
        ) : (
        <ul className="mt-8 space-y-3">
          {items.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => openAnalysis(item)}
                className="w-full rounded-xl bg-dark-card border border-dark-border p-4 text-left hover:bg-dark-input/60 hover:border-accent-green/40 transition"
              >
                <p className="font-semibold text-white">
                  {item.home_team} vs {item.away_team}
                </p>
                <p className="text-zinc-500 text-sm mt-1">{formatDate(item.created_at)}</p>
              </button>
            </li>
          ))}
        </ul>
        )}
      </div>
    </div>
  );
}
