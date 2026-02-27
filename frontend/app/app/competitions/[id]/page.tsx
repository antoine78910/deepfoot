"use client";

import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAppBasePath } from "@/contexts/AppBasePathContext";
import { useEffect, useState, useMemo } from "react";
import { getCompetitionById, currentSeasonYear } from "@/lib/competitions";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const LOGO_BASE = "https://media.api-sports.io/football/leagues";

type TabId = "analysis" | "standings" | "fixtures" | "players" | "teams";
type StandingsSubTab = "league" | "bracket";

type StandingRow = {
  rank: number;
  team: { id: number; name: string; logo: string | null };
  points: number;
  goalsDiff?: number;
  all?: { played: number; win: number; draw: number; lose: number };
};

type FixtureItem = {
  date: string;
  time: string;
  home_team: string;
  away_team: string;
  home_logo: string | null;
  away_logo: string | null;
  home_goals: number | null;
  away_goals: number | null;
};

type TeamItem = { id: number; name: string; logo: string | null };

// Icônes
function ChartIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <line x1="12" y1="20" x2="12" y2="10" /><line x1="18" y1="20" x2="18" y2="4" /><line x1="6" y1="20" x2="6" y2="16" />
    </svg>
  );
}
function TrophyIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" /><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
      <path d="M4 22h16" /><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" />
      <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" /><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" />
    </svg>
  );
}
function CalendarIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  );
}
function TargetIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" />
    </svg>
  );
}
function UsersIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}
function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

export default function CompetitionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const basePath = useAppBasePath();
  const id = typeof params?.id === "string" ? parseInt(params.id, 10) : NaN;
  const competition = useMemo(() => (Number.isNaN(id) ? null : getCompetitionById(id)), [id]);

  const [tab, setTab] = useState<TabId>("analysis");
  const [standingsSubTab, setStandingsSubTab] = useState<StandingsSubTab>("league");

  const [standings, setStandings] = useState<StandingRow[]>([]);
  const [fixtures, setFixtures] = useState<FixtureItem[]>([]);
  const [teams, setTeams] = useState<TeamItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);

  const seasonYear = currentSeasonYear();

  useEffect(() => {
    if (!competition || Number.isNaN(id)) return;
    setLoading(true);
    const season = seasonYear;
    Promise.all([
      fetch(`${API_URL}/competitions/${id}/standings?season=${season}`).then((r) => r.json()).then((d) => d.standings || []).catch(() => []),
      fetch(`${API_URL}/competitions/${id}/fixtures?season=${season}&limit=15`).then((r) => r.json()).then((d) => d.fixtures || []).catch(() => []),
      fetch(`${API_URL}/competitions/${id}/teams?season=${season}`).then((r) => r.json()).then((d) => d.teams || []).catch(() => []),
    ]).then(([s, f, t]) => {
      setStandings(Array.isArray(s) ? s : []);
      setFixtures(Array.isArray(f) ? f : []);
      setTeams(Array.isArray(t) ? t : []);
    }).finally(() => setLoading(false));
  }, [id, competition, seasonYear]);

  // Win probability mock: from standings order or equal spread
  const winProbability = useMemo(() => {
    if (standings.length === 0) return [];
    const total = 100;
    const n = Math.min(standings.length, 10);
    const probs: { team: StandingRow["team"]; pct: number }[] = [];
    let remaining = total;
    for (let i = 0; i < n; i++) {
      const pct = i < n - 1 ? Math.round(remaining * (0.25 - i * 0.02)) : remaining;
      remaining -= pct;
      probs.push({ team: standings[i].team, pct: Math.max(0, pct) });
    }
    return probs.sort((a, b) => b.pct - a.pct);
  }, [standings]);

  // Top scorers mock (API could provide later)
  const topScorers = useMemo(() => {
    return [
      { rank: 1, name: "Kylian Mbappé", club: "Real Madrid", photo: null, clubLogo: null },
      { rank: 2, name: "A. Gordon", club: "Newcastle", photo: null, clubLogo: null },
      { rank: 3, name: "H. Kane", club: "Bayern München", photo: null, clubLogo: null },
      { rank: 4, name: "E. Haaland", club: "Manchester City", photo: null, clubLogo: null },
      { rank: 5, name: "J. Hauge", club: "Bodo/Glimt", photo: null, clubLogo: null },
    ];
  }, []);

  const tabStyle = (t: TabId) =>
    tab === t
      ? "bg-[#00ffe8]/15 border border-[#00ffe8]/70 text-[#00ffe8]"
      : "border border-transparent text-zinc-400 hover:text-white";

  if (!competition) {
    return (
      <div className="p-8 text-center text-zinc-400">
        <p>Competition not found.</p>
        <Link href={`${basePath}/competitions`} className="text-[#00ffe8] mt-2 inline-block">← Back to competitions</Link>
      </div>
    );
  }

  const typeLabel = competition.type === "cup" ? "Cup" : "League";
  const subtitle = `${competition.region} - ${typeLabel} - ${competition.season}`;

  return (
    <div className="p-6 md:p-8 w-full max-w-5xl mx-auto">
      <Link
        href={`${basePath}/competitions`}
        className="inline-flex items-center gap-2 text-zinc-400 hover:text-[#00ffe8] mb-6"
      >
        ← Back to competitions
      </Link>

      <div className="rounded-xl bg-dark-card border border-dark-border p-4 mb-6 flex items-center gap-4">
        <img
          src={`${LOGO_BASE}/${competition.id}.png`}
          alt=""
          className="w-14 h-14 object-contain bg-white/5 rounded-lg"
        />
        <div>
          <h1 className="text-xl font-bold text-white">{competition.name}</h1>
          <p className="text-zinc-500 text-sm">{subtitle}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 mb-4">
        {[
          { id: "analysis" as TabId, label: "Analysis", icon: ChartIcon, count: null },
          { id: "standings" as TabId, label: "Standings", icon: TrophyIcon, count: standings.length },
          { id: "fixtures" as TabId, label: "Fixtures", icon: CalendarIcon, count: fixtures.length },
          { id: "players" as TabId, label: "Players", icon: TargetIcon, count: topScorers.length },
          { id: "teams" as TabId, label: "Teams", icon: UsersIcon, count: teams.length },
        ].map(({ id: t, label, icon: Icon, count }) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`flex items-center gap-2 rounded-lg px-4 py-2 transition ${tabStyle(t)}`}
          >
            <Icon className="w-5 h-5 flex-shrink-0" />
            <span>{label}</span>
            {count != null && count > 0 && (
              <span className="bg-zinc-700 text-zinc-300 text-xs px-2 py-0.5 rounded-full">{count}</span>
            )}
          </button>
        ))}
      </div>

      {loading && (
        <div className="text-zinc-500 py-8 text-center">Loading…</div>
      )}

      {!loading && tab === "analysis" && (
        <div className="space-y-6">
          <p className="text-zinc-500 text-sm">
            152 matches played – 0 league matches remaining – 23 bracket matches remaining – 10,000 simulations
          </p>
          {winProbability.length > 0 && (
            <>
              <div className="rounded-xl bg-dark-card border border-dark-border p-6">
                <h3 className="text-white font-semibold mb-2 flex items-center gap-2">
                  <TrophyIcon className="w-5 h-5 text-[#00ffe8]" /> FAVORITE
                </h3>
                <div className="flex items-center gap-4">
                  {winProbability[0].team.logo && (
                    <img src={winProbability[0].team.logo} alt="" className="w-16 h-16 object-contain" />
                  )}
                  <div>
                    <p className="text-white font-medium">{winProbability[0].team.name}</p>
                    <p className="text-[#00ffe8] text-xl font-bold">{winProbability[0].pct}% chance of winning the competition</p>
                  </div>
                </div>
              </div>
              <div className="rounded-xl bg-dark-card border border-dark-border p-6">
                <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
                  <TrophyIcon className="w-5 h-5 text-[#00ffe8]" /> Win probability
                </h3>
                <ul className="space-y-3">
                  {winProbability.map(({ team, pct }, i) => (
                    <li key={team.id} className="flex items-center gap-4">
                      {team.logo && <img src={team.logo} alt="" className="w-8 h-8 object-contain" />}
                      <span className="text-white flex-1 min-w-0 truncate">{team.name}</span>
                      <span className="text-[#00ffe8] font-medium w-12 text-right">{pct}%</span>
                      <div className="w-32 h-2 bg-dark-input rounded-full overflow-hidden">
                        <div className="h-full bg-[#00ffe8] rounded-full" style={{ width: `${pct}%` }} />
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
          {winProbability.length === 0 && (
            <p className="text-zinc-500">No standings data yet for win probability.</p>
          )}
        </div>
      )}

      {!loading && tab === "standings" && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setStandingsSubTab("league")}
              className={`rounded-lg px-4 py-2 text-sm ${standingsSubTab === "league" ? "bg-[#00ffe8]/15 border border-[#00ffe8]/70 text-[#00ffe8]" : "bg-dark-card border border-dark-border text-zinc-400"}`}
            >
              League phase
            </button>
            <button
              type="button"
              onClick={() => setStandingsSubTab("bracket")}
              className={`rounded-lg px-4 py-2 text-sm ${standingsSubTab === "bracket" ? "bg-[#00ffe8]/15 border border-[#00ffe8]/70 text-[#00ffe8]" : "bg-dark-card border border-dark-border text-zinc-400"}`}
            >
              Bracket
            </button>
          </div>
          {standingsSubTab === "league" && (
            <div className="rounded-xl bg-dark-card border border-dark-border overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-dark-border text-zinc-500">
                      <th className="p-3">#</th>
                      <th className="p-3">Team</th>
                      <th className="p-3 text-center">P</th>
                      <th className="p-3 text-center">GD</th>
                      <th className="p-3 text-center">Pts</th>
                    </tr>
                  </thead>
                  <tbody>
                    {standings.map((row) => (
                      <tr key={row.team?.id ?? row.rank} className="border-b border-dark-border/50 hover:bg-dark-input/30">
                        <td className="p-3 text-zinc-400">{row.rank}</td>
                        <td className="p-3">
                          <div className="flex items-center gap-2">
                            {row.team?.logo && <img src={row.team.logo} alt="" className="w-6 h-6 object-contain" />}
                            <span className="text-white">{row.team?.name ?? "—"}</span>
                          </div>
                        </td>
                        <td className="p-3 text-center text-zinc-400">{row.all?.played ?? "—"}</td>
                        <td className="p-3 text-center text-zinc-400">{row.goalsDiff ?? "—"}</td>
                        <td className="p-3 text-center text-[#00ffe8] font-medium">{row.points ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {standings.length === 0 && <p className="p-6 text-zinc-500 text-center">No standings available.</p>}
            </div>
          )}
          {standingsSubTab === "bracket" && (
            <div className="rounded-xl bg-dark-card border border-dark-border p-6 overflow-x-auto">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-white font-semibold flex items-center gap-2">
                  <TrophyIcon className="w-5 h-5 text-[#00ffe8]" /> Bracket
                </h3>
                <p className="text-zinc-500 text-xs">
                  Knockout Playoffs → Round of 16 → Quarter-finals → Semi-finals
                </p>
              </div>

              {/* Upper bracket */}
              <div className="text-[11px] font-semibold tracking-[0.18em] uppercase text-zinc-500 mb-2">
                Upper bracket
              </div>
              <div className="grid grid-cols-4 gap-6 mb-8 min-w-[920px] text-sm">
                {/* Knockout playoffs */}
                <div className="space-y-3">
                  <p className="text-[11px] font-semibold tracking-[0.18em] uppercase text-zinc-500 mb-1">
                    Knockout playoffs
                  </p>
                  {[
                    { home: "Borussia Dortmund", homeScore: 2, away: "Atalanta", awayScore: 1 },
                    { home: "Benfica", homeScore: 0, away: "Real Madrid", awayScore: 1 },
                    { home: "Galatasaray", homeScore: 5, away: "Juventus", awayScore: 2 },
                    { home: "Monaco", homeScore: 2, away: "Paris Saint Germain", awayScore: 3 },
                  ].map((m) => (
                    <div
                      key={m.home + m.away}
                      className="rounded-lg bg-[#15151f] border border-white/5 px-3 py-2.5 space-y-1.5"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 min-w-0">
                          <div className="w-6 h-6 rounded-full bg-white/5" />
                          <span className="text-xs text-white truncate">{m.home}</span>
                        </div>
                        <span className="text-xs font-semibold text-white">{m.homeScore}</span>
                      </div>
                      <div className="flex items-center justify-between gap-3 opacity-80">
                        <div className="flex items-center gap-2 min-w-0">
                          <div className="w-6 h-6 rounded-full bg-white/5" />
                          <span className="text-xs text-zinc-300 truncate">{m.away}</span>
                        </div>
                        <span className="text-xs font-semibold text-zinc-300">{m.awayScore}</span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Round of 16 */}
                <div className="space-y-3">
                  <p className="text-[11px] font-semibold tracking-[0.18em] uppercase text-zinc-500 mb-1">
                    Round of 16
                  </p>
                  {[
                    { home: "Arsenal", away: "Bayern München", winner: "Arsenal" },
                    { home: "Atalanta", away: "TBD", winner: "Atalanta" },
                    { home: "Sporting CP", away: "Manchester City", winner: "Real Madrid" },
                    { home: "Liverpool", away: "Tottenham", winner: "Galatasaray" },
                    { home: "Barcelona", away: "Chelsea", winner: "Paris Saint Germain" },
                  ].map((m, idx) => (
                    <div
                      key={m.home + m.away + idx}
                      className="rounded-lg bg-[#15151f] border border-white/5 px-3 py-2.5 space-y-1.5"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="w-6 h-6 rounded-full bg-white/5" />
                        <span className="text-xs text-white truncate">{m.home}</span>
                      </div>
                      <div className="flex items-center gap-2 min-w-0 opacity-80">
                        <div className="w-6 h-6 rounded-full bg-white/5" />
                        <span className="text-xs text-zinc-300 truncate">{m.away}</span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Quarter-finals */}
                <div className="space-y-3">
                  <p className="text-[11px] font-semibold tracking-[0.18em] uppercase text-zinc-500 mb-1">
                    Quarter-finals
                  </p>
                  {[1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className="rounded-lg border border-dashed border-zinc-600/60 bg-[#111118] px-3 py-3 flex items-center justify-between gap-3 text-xs text-zinc-400"
                    >
                      <div className="flex items-center gap-2">
                        <span className="inline-flex w-4 h-4 rounded border border-zinc-500/70" />
                        <span>TBD</span>
                      </div>
                      <span className="text-[10px] uppercase tracking-wide text-zinc-500">To be decided</span>
                    </div>
                  ))}
                </div>

                {/* Semi-finals */}
                <div className="space-y-3">
                  <p className="text-[11px] font-semibold tracking-[0.18em] uppercase text-zinc-500 mb-1">
                    Semi-finals
                  </p>
                  {[1, 2].map((i) => (
                    <div
                      key={i}
                      className="rounded-lg border border-dashed border-zinc-600/60 bg-[#111118] px-3 py-3 flex items-center justify-between gap-3 text-xs text-zinc-400"
                    >
                      <div className="flex items-center gap-2">
                        <span className="inline-flex w-4 h-4 rounded border border-zinc-500/70" />
                        <span>TBD</span>
                      </div>
                      <span className="text-[10px] uppercase tracking-wide text-zinc-500">To be decided</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Lower bracket */}
              <div className="text-[11px] font-semibold tracking-[0.18em] uppercase text-zinc-500 mb-2 mt-4">
                Lower bracket
              </div>
              <div className="grid grid-cols-4 gap-6 min-w-[920px] text-sm">
                {/* Knockout playoffs */}
                <div className="space-y-3">
                  <p className="text-[11px] font-semibold tracking-[0.18em] uppercase text-zinc-500 mb-1">
                    Knockout playoffs
                  </p>
                  {[
                    { home: "Olympiakos Piraeus", homeScore: 0, away: "Bayer Leverkusen", awayScore: 2 },
                    { home: "Bodo/Glimt", homeScore: 3, away: "Inter", awayScore: 1 },
                  ].map((m) => (
                    <div
                      key={m.home + m.away}
                      className="rounded-lg bg-[#15151f] border border-white/5 px-3 py-2.5 space-y-1.5"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2 min-w-0">
                          <div className="w-6 h-6 rounded-full bg-white/5" />
                          <span className="text-xs text-white truncate">{m.home}</span>
                        </div>
                        <span className="text-xs font-semibold text-white">{m.homeScore}</span>
                      </div>
                      <div className="flex items-center justify-between gap-3 opacity-80">
                        <div className="flex items-center gap-2 min-w-0">
                          <div className="w-6 h-6 rounded-full bg-white/5" />
                          <span className="text-xs text-zinc-300 truncate">{m.away}</span>
                        </div>
                        <span className="text-xs font-semibold text-zinc-300">{m.awayScore}</span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Round of 16 */}
                <div className="space-y-3">
                  <p className="text-[11px] font-semibold tracking-[0.18em] uppercase text-zinc-500 mb-1">
                    Round of 16
                  </p>
                  {[
                    { home: "Arsenal", away: "Bayern München" },
                    { home: "Bayer Leverkusen", away: "TBD" },
                    { home: "Sporting CP", away: "Manchester City" },
                    { home: "Bodo/Glimt", away: "TBD" },
                  ].map((m, idx) => (
                    <div
                      key={m.home + m.away + idx}
                      className="rounded-lg bg-[#15151f] border border-white/5 px-3 py-2.5 space-y-1.5"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="w-6 h-6 rounded-full bg-white/5" />
                        <span className="text-xs text-white truncate">{m.home}</span>
                      </div>
                      <div className="flex items-center gap-2 min-w-0 opacity-80">
                        <div className="w-6 h-6 rounded-full bg-white/5" />
                        <span className="text-xs text-zinc-300 truncate">{m.away}</span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Quarter-finals & Semi-finals place-holders */}
                <div className="space-y-3">
                  <p className="text-[11px] font-semibold tracking-[0.18em] uppercase text-zinc-500 mb-1">
                    Quarter-finals
                  </p>
                  {[1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className="rounded-lg border border-dashed border-zinc-600/60 bg-[#111118] px-3 py-3 flex items-center justify-between gap-3 text-xs text-zinc-400"
                    >
                      <div className="flex items-center gap-2">
                        <span className="inline-flex w-4 h-4 rounded border border-zinc-500/70" />
                        <span>TBD</span>
                      </div>
                      <span className="text-[10px] uppercase tracking-wide text-zinc-500">To be decided</span>
                    </div>
                  ))}
                </div>
                <div className="space-y-3">
                  <p className="text-[11px] font-semibold tracking-[0.18em] uppercase text-zinc-500 mb-1">
                    Semi-finals
                  </p>
                  {[1, 2].map((i) => (
                    <div
                      key={i}
                      className="rounded-lg border border-dashed border-zinc-600/60 bg-[#111118] px-3 py-3 flex items-center justify-between gap-3 text-xs text-zinc-400"
                    >
                      <div className="flex items-center gap-2">
                        <span className="inline-flex w-4 h-4 rounded border border-zinc-500/70" />
                        <span>TBD</span>
                      </div>
                      <span className="text-[10px] uppercase tracking-wide text-zinc-500">To be decided</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {!loading && tab === "fixtures" && (
        <div className="rounded-xl bg-dark-card border border-dark-border overflow-hidden">
          <h3 className="text-white font-semibold p-4 flex items-center gap-2 border-b border-dark-border">
            <CheckIcon className="w-5 h-5 text-[#00ffe8]" /> Recent results
          </h3>
          <ul className="divide-y divide-dark-border">
            {fixtures.length === 0 && <li className="p-6 text-zinc-500 text-center">No recent results.</li>}
            {fixtures.map((f, i) => {
              const homeWins = f.home_goals != null && f.away_goals != null && f.home_goals > f.away_goals;
              const awayWins = f.home_goals != null && f.away_goals != null && f.away_goals > f.home_goals;
              const dateLabel = f.date && f.time ? `${f.date.slice(8, 10)} ${["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][parseInt(f.date.slice(5, 7), 10) - 1]}, ${f.time.slice(0, 5)}` : "";
              return (
                <li key={i} className="flex items-center gap-4 p-4 hover:bg-dark-input/20">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    {f.home_logo && <img src={f.home_logo} alt="" className="w-8 h-8 object-contain flex-shrink-0" />}
                    <span className="text-white truncate">{f.home_team}</span>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className={homeWins ? "text-[#00ffe8] font-semibold" : "text-zinc-400"}>{f.home_goals ?? "—"}</span>
                    <span className="text-zinc-500">-</span>
                    <span className={awayWins ? "text-[#00ffe8] font-semibold" : "text-zinc-400"}>{f.away_goals ?? "—"}</span>
                  </div>
                  <span className="text-zinc-500 text-sm w-28">{dateLabel}</span>
                  <div className="flex items-center gap-2 min-w-0 flex-1 justify-end">
                    <span className="text-white truncate">{f.away_team}</span>
                    {f.away_logo && <img src={f.away_logo} alt="" className="w-8 h-8 object-contain flex-shrink-0" />}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {!loading && tab === "players" && (
        <div className="rounded-xl bg-dark-card border border-dark-border overflow-hidden">
          <h3 className="text-white font-semibold p-4 flex items-center gap-2 border-b border-dark-border">
            <TargetIcon className="w-5 h-5 text-[#00ffe8]" /> Top scorers
          </h3>
          <ul className="divide-y divide-dark-border">
            {topScorers.map((p) => (
              <li key={p.rank} className="flex items-center gap-4 p-4 hover:bg-dark-input/20">
                <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 ${
                  p.rank === 1 ? "bg-amber-500/20 text-amber-400" : p.rank === 2 ? "bg-zinc-400/20 text-zinc-300" : p.rank === 3 ? "bg-amber-700/30 text-amber-600" : "bg-dark-input text-zinc-400"
                }`}>
                  {p.rank}
                </span>
                <div className="w-10 h-10 rounded-full bg-dark-input flex-shrink-0" />
                <div className="min-w-0 flex-1">
                  <p className="text-white font-medium">{p.name}</p>
                  <p className="text-zinc-500 text-sm">{p.club}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!loading && tab === "teams" && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {teams.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setSelectedTeamId(selectedTeamId === t.id ? null : t.id)}
                className={`rounded-xl bg-dark-card border p-4 flex flex-col items-center gap-2 transition hover:border-[#00ffe8]/50 ${selectedTeamId === t.id ? "border-[#00ffe8]/70" : "border-dark-border"}`}
              >
                {t.logo && <img src={t.logo} alt="" className="w-12 h-12 object-contain" />}
                <span className="text-white text-sm font-medium text-center truncate w-full">{t.name}</span>
              </button>
            ))}
          </div>
          {teams.length === 0 && <p className="text-zinc-500 text-center py-8">No teams loaded.</p>}
          {selectedTeamId != null && (
            <div className="rounded-xl bg-dark-card border border-dark-border p-6">
              <h3 className="text-white font-semibold mb-2">Stats détaillées de l&apos;équipe</h3>
              <p className="text-zinc-500 text-sm">
                Les statistiques détaillées pour l&apos;équipe sélectionnée seront disponibles ici (à venir).
              </p>
              <p className="text-zinc-500 text-sm mt-2">Team ID: {selectedTeamId}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
