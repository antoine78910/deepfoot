"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AnalysisResult } from "@/components/AnalysisResult";
import { useLanguage } from "@/contexts/LanguageContext";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AppAnalysisPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const prevLangRef = useRef<string | null>(null);
  const { t, lang } = useLanguage();

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
          params.set("_t", String(Date.now()));
          fetch(`${API_URL}/predict/match-result?${params}`)
            .then((r) => (r.ok ? r.json() : null))
            .then((enrich) => {
              if (enrich && typeof enrich === "object") {
                setData((prev) => {
                  if (!prev) return prev;
                  const next = { ...prev };
                  if (enrich.match_over !== undefined) next.match_over = enrich.match_over;
                  if (enrich.match_over === true) {
                    next.final_score_home = typeof enrich.final_score_home === "number" ? enrich.final_score_home : Number(enrich.final_score_home) || 0;
                    next.final_score_away = typeof enrich.final_score_away === "number" ? enrich.final_score_away : Number(enrich.final_score_away) || 0;
                    if (Array.isArray(enrich.match_statistics)) next.match_statistics = enrich.match_statistics;
                  } else {
                    if (enrich.final_score_home !== undefined) next.final_score_home = typeof enrich.final_score_home === "number" ? enrich.final_score_home : Number(enrich.final_score_home) ?? 0;
                    if (enrich.final_score_away !== undefined) next.final_score_away = typeof enrich.final_score_away === "number" ? enrich.final_score_away : Number(enrich.final_score_away) ?? 0;
                    if (Array.isArray(enrich.match_statistics) && enrich.match_statistics.length > 0)
                      next.match_statistics = enrich.match_statistics;
                  }
                  return next;
                });
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

  // When user changes language, translate current analysis in place
  useEffect(() => {
    if (!data || typeof data !== "object") return;
    if (prevLangRef.current === null) {
      prevLangRef.current = lang;
      return;
    }
    if (prevLangRef.current === lang) return;
    prevLangRef.current = lang;
    fetch(`${API_URL}/predict/translate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analysis: data, target_lang: lang }),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((translated) => {
        if (translated && typeof translated === "object") setData(translated);
      })
      .catch(() => {});
  }, [lang, data]);

  if (data === null) {
    return (
      <div className="p-4 sm:p-8 w-full flex flex-col items-center">
        <div className="w-full max-w-xl mx-auto">
          <p className="text-zinc-400 mb-4">{t("analysis.noData")}</p>
          <Link href="/matches" className="text-accent-cyan hover:underline">{t("history.analyzeMatch")}</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-8 pb-16 w-full flex flex-col items-center">
      <div className="w-full max-w-4xl mx-auto">
        <Link href="/matches" className="inline-block text-zinc-500 hover:text-accent-cyan text-sm mb-8">
          ← {t("analysis.newAnalysis")}
        </Link>
        <AnalysisResult result={data} />
      </div>
    </div>
  );
}
