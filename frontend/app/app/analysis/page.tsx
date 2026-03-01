"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AnalysisResult } from "@/components/AnalysisResult";
import { useLanguage } from "@/contexts/LanguageContext";
import { useAppBasePath } from "@/contexts/AppBasePathContext";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AppAnalysisPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const { t } = useLanguage();
  const basePath = useAppBasePath();

  useEffect(() => {
    const raw = sessionStorage.getItem("visifoot_analysis");
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as Record<string, unknown>;
        setData(parsed);
        const home = typeof parsed?.home_team === "string" ? parsed.home_team.trim() : "";
        const away = typeof parsed?.away_team === "string" ? parsed.away_team.trim() : "";
        if (home && away) {
          const params = new URLSearchParams({ home_team: home, away_team: away });
          fetch(`${API_URL}/predict/match-result?${params}`)
            .then((r) => (r.ok ? r.json() : null))
            .then((enrich) => {
              if (enrich && typeof enrich === "object") {
                setData((prev) =>
                  prev
                    ? {
                        ...prev,
                        match_over: enrich.match_over,
                        final_score_home: enrich.final_score_home,
                        final_score_away: enrich.final_score_away,
                        match_statistics: enrich.match_statistics,
                      }
                    : prev
                );
              }
            })
            .catch(() => {});
        }
      } catch {
        setData(null);
      }
    } else {
      setData(null);
    }
  }, []);

  if (data === null) {
    return (
      <div className="p-8 w-full flex flex-col items-center">
        <div className="w-full max-w-xl mx-auto">
          <p className="text-zinc-400 mb-4">{t("analysis.noData")}</p>
          <Link href={`${basePath}/matches`} className="text-accent-cyan hover:underline">{t("history.analyzeMatch")}</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 pb-16 w-full flex flex-col items-center">
      <div className="w-full max-w-4xl mx-auto">
        <Link href={`${basePath}/matches`} className="inline-block text-zinc-500 hover:text-accent-cyan text-sm mb-8">
          ← {t("analysis.newAnalysis")}
        </Link>
        <AnalysisResult result={data} />
      </div>
    </div>
  );
}
