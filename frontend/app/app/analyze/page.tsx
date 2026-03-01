"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AnalysisResult } from "@/components/AnalysisResult";
import { useLanguage } from "@/contexts/LanguageContext";
import { useAppBasePath } from "@/contexts/AppBasePathContext";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const HISTORY_KEY = "visifoot_history";

function AnalyzeContent() {
  const searchParams = useSearchParams();
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [notFound, setNotFound] = useState(false);
  const { t } = useLanguage();
  const basePath = useAppBasePath();

  const team1 = searchParams.get("team1") ?? "";
  const team2 = searchParams.get("team2") ?? "";
  const fromHistory = searchParams.get("fromHistory") === "true";
  const predictionId = searchParams.get("predictionId") ?? "";

  useEffect(() => {
    if (!fromHistory || !predictionId) {
      setNotFound(true);
      return;
    }
    try {
      const raw = localStorage.getItem(HISTORY_KEY);
      const list: { id: string; result: Record<string, unknown> }[] = raw ? JSON.parse(raw) : [];
      const item = list.find((x) => x.id === predictionId);
      if (!item?.result) {
        setNotFound(true);
        return;
      }
      const parsed = item.result as Record<string, unknown>;
      setData(parsed);
      const home = team1.trim() || (typeof parsed?.home_team === "string" ? parsed.home_team.trim() : "");
      const away = team2.trim() || (typeof parsed?.away_team === "string" ? parsed.away_team.trim() : "");
      if (home && away) {
        const params = new URLSearchParams({ home_team: home, away_team: away });
        const hid = parsed?.home_team_id;
        const aid = parsed?.away_team_id;
        if (typeof hid === "number" && !Number.isNaN(hid)) params.set("home_team_id", String(hid));
        if (typeof aid === "number" && !Number.isNaN(aid)) params.set("away_team_id", String(aid));
        fetch(`${API_URL}/predict/match-result?${params}`)
          .then((r) => (r.ok ? r.json() : null))
          .then((enrich) => {
            if (enrich && typeof enrich === "object") {
              setData((prev) =>
                prev
                  ? {
                      ...prev,
                      match_over: enrich.match_over ?? prev.match_over,
                      final_score_home: enrich.final_score_home ?? prev.final_score_home,
                      final_score_away: enrich.final_score_away ?? prev.final_score_away,
                      match_statistics: enrich.match_statistics ?? prev.match_statistics,
                    }
                  : prev
              );
            }
          })
          .catch(() => {});
      }
    } catch {
      setNotFound(true);
    }
  }, [fromHistory, predictionId, team1, team2]);

  if (notFound) {
    return (
      <div className="p-8 w-full flex flex-col items-center">
        <div className="w-full max-w-xl mx-auto">
          <p className="text-zinc-400 mb-4">{t("analysis.noData")}</p>
          <Link href={`${basePath}/history`} className="text-accent-cyan hover:underline">
            ← {t("history.title")}
          </Link>
          <span className="text-zinc-500 mx-2">|</span>
          <Link href={`${basePath}/matches`} className="text-accent-cyan hover:underline">
            {t("history.analyzeMatch")}
          </Link>
        </div>
      </div>
    );
  }

  if (data === null) {
    return (
      <div className="p-8 w-full flex flex-col items-center">
        <div className="w-full max-w-xl mx-auto">
          <p className="text-zinc-400">Loading…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 pb-16 w-full flex flex-col items-center">
      <div className="w-full max-w-4xl mx-auto">
        <Link href={`${basePath}/history`} className="inline-block text-zinc-500 hover:text-accent-cyan text-sm mb-8">
          ← {t("history.title")}
        </Link>
        <AnalysisResult result={data} />
      </div>
    </div>
  );
}

export default function AnalyzePage() {
  return (
    <Suspense fallback={<div className="p-8 text-zinc-400 text-center">Loading…</div>}>
      <AnalyzeContent />
    </Suspense>
  );
}
