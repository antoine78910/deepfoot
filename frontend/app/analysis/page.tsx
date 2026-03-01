"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AnalysisResult } from "@/components/AnalysisResult";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AnalysisPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);

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
      <main className="min-h-screen flex flex-col items-center justify-center px-4">
        <p className="text-zinc-400 mb-4">No analysis data. Start by analyzing a match.</p>
        <Link href="/" className="text-[#00ffe8] hover:underline">Back to home</Link>
      </main>
    );
  }

  return (
    <main className="min-h-screen px-4 py-8 pb-16 max-w-4xl mx-auto">
      <Link href="/" className="inline-block text-zinc-500 hover:text-[#00ffe8] text-sm mb-8">
        ← New analysis
      </Link>
      <AnalysisResult result={data} />
    </main>
  );
}
