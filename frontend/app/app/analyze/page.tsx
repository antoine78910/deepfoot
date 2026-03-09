"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AnalysisResult } from "@/components/AnalysisResult";
import { useLanguage } from "@/contexts/LanguageContext";
import { getHistoryKey, getUserFromStorage } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function AnalyzeContent() {
  const searchParams = useSearchParams();
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [notFound, setNotFound] = useState(false);
  const prevLangRef = useRef<string | null>(null);
  const { t, lang } = useLanguage();

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
      const key = getHistoryKey();
      const raw = localStorage.getItem(key);
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
      setNotFound(true);
    }
  }, [fromHistory, predictionId, team1, team2]);

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

  if (notFound) {
    return (
      <div className="px-2 py-4 sm:p-8 w-full flex flex-col items-center">
        <div className="w-full max-w-xl mx-auto min-w-0">
          <p className="text-zinc-400 mb-4">{t("analysis.noData")}</p>
          <Link href="/history" className="text-accent-cyan hover:underline">
            ← {t("history.title")}
          </Link>
          <span className="text-zinc-500 mx-2">|</span>
          <Link href="/matches" className="text-accent-cyan hover:underline">
            {t("history.analyzeMatch")}
          </Link>
        </div>
      </div>
    );
  }

  if (data === null) {
    return (
      <div className="px-2 py-4 sm:p-8 w-full flex flex-col items-center">
        <div className="w-full max-w-xl mx-auto min-w-0">
          <p className="text-zinc-400">Loading…</p>
        </div>
      </div>
    );
  }

  // Depuis l'historique, le résultat sauvegardé peut avoir full_analysis: false (analyse faite en free).
  // Si l'utilisateur a maintenant un plan payant, on affiche l'analyse complète.
  const user = getUserFromStorage();
  const hasPaidPlan = user?.plan && user.plan !== "free";
  const resultToShow = hasPaidPlan ? { ...data, full_analysis: true } : data;

  return (
    <div className="px-2 py-4 sm:p-8 pb-16 w-full flex flex-col items-center">
      <div className="w-full max-w-4xl mx-auto min-w-0">
        <Link href="/history" className="inline-block text-zinc-500 hover:text-accent-cyan text-sm mb-8">
          ← {t("history.title")}
        </Link>
        <AnalysisResult result={resultToShow} />
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
