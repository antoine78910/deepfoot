"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { TeamAutocomplete, type TeamOption } from "./TeamAutocomplete";
import { getApiUrl } from "@/lib/api";

type UpcomingFixture = {
  date: string;
  time: string;
  league?: { name: string | null } | null;
  home: { name: string; logo: string | null };
  away: { name: string; logo: string | null };
};

type LandingMatchSearchProps = {
  /** Base URL for analyse page (e.g. /analyse or https://app.example.com/analyse) */
  analyseHref?: string;
};

export function LandingMatchSearch({ analyseHref = "/analyse" }: LandingMatchSearchProps) {
  const [teamQuery, setTeamQuery] = useState("");
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);
  const [selectedTeamId, setSelectedTeamId] = useState<number | string | null>(null);
  const [upcoming, setUpcoming] = useState<UpcomingFixture[]>([]);
  const [loadingUpcoming, setLoadingUpcoming] = useState(false);

  const [apiUrl, setApiUrl] = useState("");
  useEffect(() => {
    setApiUrl(getApiUrl());
  }, []);

  useEffect(() => {
    if (!apiUrl) return;
    if (!selectedTeam?.trim() && selectedTeamId == null) {
      setUpcoming([]);
      return;
    }
    setLoadingUpcoming(true);
    const params = new URLSearchParams({ limit: "10" });
    if (selectedTeam?.trim()) params.set("team", selectedTeam.trim());
    if (selectedTeamId != null && selectedTeamId !== "") params.set("team_id", String(selectedTeamId));
    fetch(`${apiUrl}/teams/upcoming?${params}`)
      .then((res) => res.json())
      .then((data) => setUpcoming(data.fixtures || []))
      .catch(() => setUpcoming([]))
      .finally(() => setLoadingUpcoming(false));
  }, [apiUrl, selectedTeam, selectedTeamId]);

  return (
    <div className="w-full max-w-xl mx-auto">
      <p className="text-zinc-500 text-xs sm:text-sm mb-2 text-center">
        Choose the match you want to analyze ⬇️
      </p>
      <div className="relative">
        <div className="absolute -inset-1 rounded-2xl bg-[#00ffe8]/20 blur-xl pointer-events-none" aria-hidden />
        <div className="relative shadow-[0_0_30px_rgba(0,255,232,0.25)] rounded-xl">
          <TeamAutocomplete
        value={teamQuery}
        onChange={setTeamQuery}
        onSelect={(team: TeamOption) => {
          setSelectedTeam(team.name.trim() || null);
          setSelectedTeamId(team.id != null ? team.id : null);
        }}
        placeholder="Search for a team (e.g. Real Madrid, PSG…)"
        debounceMs={0}
        fetchLimit={20}
      />
        </div>
      </div>

      <p className="text-zinc-500 text-xs text-center mt-2">
        1198 matches analyzed this week
      </p>
      <div className="flex justify-center mt-8 mb-2">
        <Link
          href={analyseHref}
          className="inline-flex items-center justify-center px-8 py-3.5 rounded-xl font-semibold text-black bg-[#00ffe8] hover:opacity-90 transition text-base"
        >
          Analyze a match with AI
        </Link>
      </div>

      {selectedTeam && (
        <div className="mt-6 p-4 rounded-2xl bg-white/5 border border-white/10">
          <h3 className="text-sm font-semibold text-white mb-1">Upcoming matches</h3>
          <p className="text-zinc-500 text-xs mb-4">Click a match to analyze it with AI</p>
          {loadingUpcoming ? (
            <div className="flex items-center justify-center gap-2 py-6 text-zinc-400 text-sm">
              <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24" aria-hidden>
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span>Loading…</span>
            </div>
          ) : upcoming.length === 0 ? (
            <p className="text-zinc-500 text-sm">No upcoming matches found.</p>
          ) : (
            <ul className="space-y-2">
              {upcoming.map((f, i) => (
                <li key={i}>
                  <Link
                    href={`${analyseHref}?home=${encodeURIComponent(f.home.name)}&away=${encodeURIComponent(f.away.name)}`}
                    className="rounded-xl bg-white/5 border border-white/10 px-4 py-2.5 text-left transition hover:bg-white/10 hover:border-[#00ffe8]/30 block"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-32 flex-shrink-0">
                        <div className="text-zinc-400 text-sm tabular-nums leading-tight whitespace-nowrap">
                          {f.date} - {f.time}
                        </div>
                        {f.league?.name ? (
                          <div className="text-[11px] text-zinc-500 leading-tight flex items-center gap-1 mt-0.5 min-w-0">
                            <span className="text-amber-300">🏆</span>
                            <span className="whitespace-nowrap overflow-hidden" title={f.league.name}>
                              {f.league.name}
                            </span>
                          </div>
                        ) : null}
                      </div>
                      <div className="flex items-center justify-center gap-4 flex-1 min-w-0">
                        <div className="flex items-center gap-2 min-w-0 flex-[0_1_13rem]">
                          {f.home.logo ? (
                            <img src={f.home.logo} alt="" className="w-7 h-7 object-contain flex-shrink-0" />
                          ) : (
                            <div className="w-7 h-7 rounded-full bg-white/10 flex-shrink-0" />
                          )}
                          <span className="text-white text-sm font-medium truncate">{f.home.name}</span>
                        </div>
                        <span className="text-zinc-500 text-xs font-medium flex-shrink-0">VS</span>
                        <div className="flex items-center gap-2 min-w-0 flex-[0_1_13rem] justify-end">
                          <span className="text-white text-sm font-medium truncate text-right">{f.away.name}</span>
                          {f.away.logo ? (
                            <img src={f.away.logo} alt="" className="w-7 h-7 object-contain flex-shrink-0" />
                          ) : (
                            <div className="w-7 h-7 rounded-full bg-white/10 flex-shrink-0" />
                          )}
                        </div>
                      </div>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
