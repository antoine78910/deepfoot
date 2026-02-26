"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { TeamAutocomplete } from "./TeamAutocomplete";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function MatchInput() {
  const [homeTeam, setHomeTeam] = useState("");
  const [awayTeam, setAwayTeam] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!homeTeam.trim() || !awayTeam.trim()) {
      setError("Veuillez saisir les deux équipes.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ home_team: homeTeam.trim(), away_team: awayTeam.trim() }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Error ${res.status}`);
      }
      const data = await res.json();
      sessionStorage.setItem("visifoot_analysis", JSON.stringify(data));
      router.push("/analysis");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-xl rounded-2xl bg-dark-card border border-dark-border p-6 shadow-glow">
      <p className="text-xs uppercase tracking-wider text-zinc-500 mb-6">Match to analyze</p>

      <form onSubmit={handleSubmit} className="space-y-6">
        <TeamAutocomplete
          value={homeTeam}
          onChange={setHomeTeam}
          placeholder="Équipe domicile (ex: Lorient, AJA…)"
          disabled={loading}
        />

        <p className="text-center text-white font-semibold text-lg">VS</p>

        <TeamAutocomplete
          value={awayTeam}
          onChange={setAwayTeam}
          placeholder="Équipe extérieur (ex: Auxerre, OM…)"
          disabled={loading}
        />

        {error && (
          <p className="text-red-400 text-sm text-center">{error}</p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-4 rounded-xl font-semibold text-white bg-gradient-to-r from-[#00d4ff] to-[#00f0a0] hover:opacity-90 transition shadow-glow disabled:opacity-60"
        >
          {loading ? "Analyzing…" : "Analyze the match with AI"}
        </button>
      </form>
    </div>
  );
}
