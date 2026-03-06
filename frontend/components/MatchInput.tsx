"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { TeamAutocomplete, type TeamOption } from "./TeamAutocomplete";
import { UnlockPricingModal, type PricingModalVariant } from "./UnlockPricingModal";
import { AnalysisStepDisplay } from "./AnalysisStepDisplay";
import { useLanguage } from "@/contexts/LanguageContext";
import { getAppHref } from "@/lib/app-url";
import { getUserFromStorage } from "@/lib/auth";

function LoaderSpinner({ className }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className ?? "w-5 h-5"}`} fill="none" viewBox="0 0 24 24" aria-hidden>
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
    </svg>
  );
}

/** Overlay de chargement style /loading-demo : fond sombre + carte centrée */
function AnalysisLoadingOverlay({
  progress,
  progressStep,
  analyzingLabel,
}: {
  progress: number;
  progressStep: string;
  analyzingLabel: string;
}) {
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center p-6 bg-[#0a0a0f]" aria-live="polite" aria-busy="true">
      <div className="w-full max-w-md rounded-2xl bg-[#14141c] border border-white/10 p-8 shadow-xl">
        <div className="flex flex-col items-center gap-4 w-full">
          <span className="flex items-center gap-2 text-white">
            <LoaderSpinner className="w-5 h-5 flex-shrink-0 text-[#00ffe8]" />
            <span className="font-semibold">{analyzingLabel}</span>
          </span>
          <span className="text-2xl font-bold tabular-nums text-white">{progress}%</span>
          <AnalysisStepDisplay
            step={progressStep}
            variant="default"
            className="w-full min-h-[2rem] text-zinc-300"
          />
          <div className="w-full h-2.5 bg-white/10 rounded-full overflow-hidden shadow-inner">
            <div
              className="h-full bg-gradient-to-r from-[#00ffe8] to-emerald-400 rounded-full transition-all duration-700 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type UpcomingFixture = {
  date: string;
  time: string;
  league?: { name: string | null } | null;
  home: { name: string; logo: string | null };
  away: { name: string; logo: string | null };
};

type MatchInputProps = {
  initialHome?: string;
  initialAway?: string;
  /** When true, submit will call onRequireAuth() instead of analyzing if !isLoggedIn */
  requireAuth?: boolean;
  isLoggedIn?: boolean;
  /** Called when user tries to submit without being logged in. Receives the two teams so post-login can redirect to /matches with them. */
  onRequireAuth?: (teams?: { home: string; away: string }) => void;
  /** When true, no analysis is run; show CTA to analyze in the app instead */
  displayOnly?: boolean;
  /** When true, use API-Football Predictions for 1X2 (if fixture found); otherwise use our Poisson model. For testing. */
  useApiPredictions?: boolean;
};

export function MatchInput({
  initialHome = "",
  initialAway = "",
  requireAuth = false,
  isLoggedIn = true,
  onRequireAuth,
  displayOnly = false,
  useApiPredictions = false,
}: MatchInputProps) {
  const [homeTeam, setHomeTeam] = useState(initialHome);
  const [awayTeam, setAwayTeam] = useState(initialAway);
  const [selectedHomeTeam, setSelectedHomeTeam] = useState<string | null>(null);
  const [selectedHomeTeamId, setSelectedHomeTeamId] = useState<number | string | null>(null);
  const [homeTeamOption, setHomeTeamOption] = useState<TeamOption | null>(null);
  const [awayTeamOption, setAwayTeamOption] = useState<TeamOption | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressStep, setProgressStep] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [limitModalVariant, setLimitModalVariant] = useState<PricingModalVariant | null>(null);
  const [upcoming, setUpcoming] = useState<UpcomingFixture[]>([]);
  const [loadingUpcoming, setLoadingUpcoming] = useState(false);
  const router = useRouter();
  const { t, lang } = useLanguage();
  const submitIdRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  // Sync from URL when landing on /analyse?home=...&away=...
  useEffect(() => {
    if (initialHome !== undefined && initialHome !== homeTeam) setHomeTeam(initialHome);
    if (initialAway !== undefined && initialAway !== awayTeam) setAwayTeam(initialAway);
  }, [initialHome, initialAway]);

  // Resolve initial home/away from URL to full TeamOption (id, crest) so blasons and "validated" state show
  useEffect(() => {
    const homeTrim = initialHome?.trim();
    const awayTrim = initialAway?.trim();
    if (!homeTrim && !awayTrim) return;

    const norm = (s: string) => s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    const matchName = (team: TeamOption, query: string) => {
      const q = norm(query);
      const n = norm(team.name);
      return n === q || n.includes(q) || q.includes(n) || n.startsWith(q);
    };

    if (homeTrim) {
      fetch(`${API_URL}/teams?q=${encodeURIComponent(homeTrim)}&limit=20`)
        .then((res) => res.json())
        .then((data: { teams?: TeamOption[] }) => {
          const list = (data.teams || []).filter((t: TeamOption) => Boolean(t?.name));
          const found = list.find((t: TeamOption) => matchName(t, homeTrim)) ?? list[0];
          if (found) {
            setHomeTeam(found.name);
            setHomeTeamOption(found);
            setSelectedHomeTeam(found.name.trim() || null);
            setSelectedHomeTeamId(found.id ?? null);
          }
        })
        .catch(() => {});
    }
    if (awayTrim) {
      fetch(`${API_URL}/teams?q=${encodeURIComponent(awayTrim)}&limit=20`)
        .then((res) => res.json())
        .then((data: { teams?: TeamOption[] }) => {
          const list = (data.teams || []).filter((t: TeamOption) => Boolean(t?.name));
          const found = list.find((t: TeamOption) => matchName(t, awayTrim)) ?? list[0];
          if (found) {
            setAwayTeam(found.name);
            setAwayTeamOption(found);
          }
        })
        .catch(() => {});
    }
  }, [initialHome, initialAway]);

  // Réinitialiser la sélection si l'utilisateur modifie le texte à la main
  useEffect(() => {
    if (!homeTeam.trim()) {
      setSelectedHomeTeam(null);
      setSelectedHomeTeamId(null);
      setHomeTeamOption(null);
    } else if (selectedHomeTeam !== null && homeTeam.trim() !== selectedHomeTeam) {
      setSelectedHomeTeam(null);
      setSelectedHomeTeamId(null);
      setHomeTeamOption(null);
    }
  }, [homeTeam, selectedHomeTeam]);

  useEffect(() => {
    if (!awayTeam.trim()) setAwayTeamOption(null);
    else if (awayTeamOption && awayTeam.trim() !== awayTeamOption.name) setAwayTeamOption(null);
  }, [awayTeam, awayTeamOption]);

  useEffect(() => {
    if (!selectedHomeTeam?.trim() && selectedHomeTeamId == null) {
      setUpcoming([]);
      return;
    }
    setLoadingUpcoming(true);
    const params = new URLSearchParams({ limit: "10" });
    if (selectedHomeTeam?.trim()) {
      params.set("team", selectedHomeTeam.trim());
    }
    if (selectedHomeTeamId != null && selectedHomeTeamId !== "") {
      params.set("team_id", String(selectedHomeTeamId));
    }
    fetch(`${API_URL}/teams/upcoming?${params}`)
      .then((res) => res.json())
      .then((data) => setUpcoming(data.fixtures || []))
      .catch(() => setUpcoming([]))
      .finally(() => setLoadingUpcoming(false));
  }, [selectedHomeTeam, selectedHomeTeamId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (displayOnly) return;
    setError(null);
    if (!homeTeam.trim() || !awayTeam.trim()) {
      setError(t("matchInput.errorTwoTeams"));
      return;
    }
    if (requireAuth && !isLoggedIn && onRequireAuth) {
      onRequireAuth({ home: homeTeam.trim(), away: awayTeam.trim() });
      return;
    }
    // Annuler une éventuelle requête précédente
    if (abortRef.current && !abortRef.current.signal.aborted) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;

    const submitId = ++submitIdRef.current;

    setLoading(true);
    setProgress(0);
    setProgressStep("");
    try {
      const body: Record<string, string | number | boolean> = {
        home_team: homeTeam.trim(),
        away_team: awayTeam.trim(),
        use_api_predictions: useApiPredictions,
        language: lang,
      };
      const homeId = homeTeamOption?.id != null ? Number(homeTeamOption.id) : NaN;
      const awayId = awayTeamOption?.id != null ? Number(awayTeamOption.id) : NaN;
      if (Number.isInteger(homeId)) body.home_team_id = homeId;
      if (Number.isInteger(awayId)) body.away_team_id = awayId;

      const user = getUserFromStorage();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (user?.id) headers["X-User-Id"] = user.id;

      const res = await fetch(`${API_URL}/predict/stream`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const detail = typeof data?.detail === "string" ? data.detail : "";
        if (res.status === 403 && (detail === "starter" || detail === "free")) {
          setLimitModalVariant(detail === "starter" ? "pro_lifetime" : "free");
          setLoading(false);
          return;
        }
        throw new Error(detail || `Error ${res.status}`);
      }
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let data: Record<string, unknown> | null = null;
      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          if (controller.signal.aborted) return;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";
          for (const line of lines) {
            if (!line.trim()) continue;
            try {
              const event = JSON.parse(line) as { type?: string; step?: string; percent?: number; data?: Record<string, unknown>; message?: string; code?: string };
              if (event.type === "progress") {
                setProgress(event.percent ?? 0);
                setProgressStep(event.step ?? "");
              } else if (event.type === "result" && event.data) {
                data = event.data as Record<string, unknown>;
              } else if (event.type === "error") {
                const code = event.code;
                if (code === "starter" || code === "free") {
                  setLimitModalVariant(code === "starter" ? "pro_lifetime" : "free");
                  setLoading(false);
                  return;
                }
                throw new Error(event.message ?? "Analysis failed.");
              }
            } catch (parseErr) {
              if (parseErr instanceof Error && parseErr.message !== "Analysis failed.") {
                // ignore JSON/parse errors for non-event lines
              } else throw parseErr;
            }
          }
        }
        // Process any remaining buffer (last line may not end with \n when stream closes)
        if (buffer.trim()) {
          try {
            const event = JSON.parse(buffer.trim()) as { type?: string; step?: string; percent?: number; data?: Record<string, unknown>; message?: string; code?: string };
            if (event.type === "result" && event.data) {
              data = event.data as Record<string, unknown>;
            } else if (event.type === "error") {
              const code = event.code;
              if (code === "starter" || code === "free") {
                setLimitModalVariant(code === "starter" ? "pro_lifetime" : "free");
                setLoading(false);
                return;
              }
              const msg = event.message ?? "Analysis failed.";
              throw new Error(typeof msg === "string" ? msg : "Analysis failed.");
            }
          } catch (parseErr) {
            if (parseErr instanceof Error && parseErr.message !== "Analysis failed.") {
              // ignore
            } else throw parseErr;
          }
        }
      }
      if (!data) throw new Error("No result from server. The match may not have predictions available yet, or the server may have timed out.");

      // Si une nouvelle soumission a été lancée entre-temps, on ignore ce résultat
      if (submitId !== submitIdRef.current) return;
      sessionStorage.setItem("visifoot_analysis", JSON.stringify(data));
      const historyKey = "visifoot_history";
      const maxHistory = 50;
      const predictionId = crypto.randomUUID();
      try {
        const raw = localStorage.getItem(historyKey);
        const list = raw ? JSON.parse(raw) : [];
        list.unshift({
          id: predictionId,
          home_team: data.home_team,
          away_team: data.away_team,
          home_logo: (data as any)?.home_team_logo ?? null,
          away_logo: (data as any)?.away_team_logo ?? null,
          league: (data as any)?.league ?? null,
          created_at: new Date().toISOString(),
          result: data,
        });
        localStorage.setItem(historyKey, JSON.stringify(list.slice(0, maxHistory)));
      } catch {
        // ignore
      }
      setProgress(100);
      setProgressStep("Done");
      await new Promise((r) => setTimeout(r, 300));
      const analyzeUrl = `/analyze?${new URLSearchParams({
        team1: String(data.home_team ?? ""),
        team2: String(data.away_team ?? ""),
        fromHistory: "true",
        predictionId,
      }).toString()}`;
      router.push(analyzeUrl);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
      setProgress(0);
      setProgressStep("");
    } finally {
      if (submitId === submitIdRef.current) {
        setLoading(false);
      }
    }
  };

  // Cleanup global: annuler la requête en cours si on quitte la page
  useEffect(() => {
    return () => {
      if (abortRef.current && !abortRef.current.signal.aborted) {
        abortRef.current.abort();
      }
    };
  }, []);

  return (
    <div className="w-full max-w-xl rounded-2xl bg-dark-card border border-dark-border p-6 shadow-glow relative">
      {loading && (
        <AnalysisLoadingOverlay
          progress={progress}
          progressStep={progressStep}
          analyzingLabel={t("matchInput.analyzing")}
        />
      )}
      <p className="text-xs uppercase tracking-wider text-zinc-500 mb-6">{t("matchInput.matchToAnalyze")}</p>

      <form onSubmit={handleSubmit} className="space-y-6">
        <TeamAutocomplete
          value={homeTeam}
          onChange={setHomeTeam}
          onSelect={(team) => {
            setSelectedHomeTeam(team.name.trim() || null);
            setSelectedHomeTeamId(team.id != null ? team.id : null);
            setHomeTeamOption(team);
          }}
          placeholder={t("matchInput.placeholderHome")}
          disabled={loading}
          debounceMs={0}
          fetchLimit={20}
          suppressSuggestions={!!homeTeamOption}
        />

        <p className="text-center text-white font-semibold text-lg">VS</p>

        <TeamAutocomplete
          value={awayTeam}
          onChange={setAwayTeam}
          onSelect={(team) => setAwayTeamOption(team)}
          placeholder={t("matchInput.placeholderAway")}
          disabled={loading}
          debounceMs={0}
          fetchLimit={20}
          suppressSuggestions={!!awayTeamOption}
        />

        {(homeTeamOption || awayTeamOption || (homeTeam.trim() && awayTeam.trim())) && (
          <div className="flex items-center justify-center gap-4 py-3 px-4 rounded-xl bg-dark-input/50 border border-dark-border">
            <div className="flex items-center gap-2 min-w-0">
              {homeTeamOption?.crest ? (
                <img src={homeTeamOption.crest} alt="" className="w-10 h-10 object-contain flex-shrink-0" />
              ) : (
                <div className="w-10 h-10 rounded-full bg-dark-card flex-shrink-0 flex items-center justify-center text-zinc-500 text-sm">?</div>
              )}
              <span className="text-white font-medium truncate">{homeTeamOption?.name || homeTeam.trim() || "—"}</span>
            </div>
            <span className="text-zinc-500 font-semibold flex-shrink-0">VS</span>
            <div className="flex items-center gap-2 min-w-0">
              {awayTeamOption?.crest ? (
                <img src={awayTeamOption.crest} alt="" className="w-10 h-10 object-contain flex-shrink-0" />
              ) : (
                <div className="w-10 h-10 rounded-full bg-dark-card flex-shrink-0 flex items-center justify-center text-zinc-500 text-sm">?</div>
              )}
              <span className="text-white font-medium truncate">{awayTeamOption?.name || awayTeam.trim() || "—"}</span>
            </div>
          </div>
        )}

        {error && (
          <p className="text-red-400 text-sm text-center">{error}</p>
        )}

        {limitModalVariant && (
          <UnlockPricingModal
            open={!!limitModalVariant}
            onClose={() => setLimitModalVariant(null)}
            variant={limitModalVariant}
          />
        )}
        {displayOnly ? (
          <Link
            href={`${getAppHref("/matches")}${homeTeam.trim() && awayTeam.trim() ? `?home=${encodeURIComponent(homeTeam.trim())}&away=${encodeURIComponent(awayTeam.trim())}` : ""}`}
            className="w-full py-4 rounded-xl font-semibold text-black bg-gradient-to-r from-[#00ffe8] to-[#00ddcc] hover:opacity-90 transition shadow-glow flex items-center justify-center"
          >
            Analyze in the app
          </Link>
        ) : (
          <button
            type="submit"
            disabled={loading}
            className="w-full py-4 rounded-xl font-semibold text-black bg-gradient-to-r from-[#00ffe8] to-[#00ddcc] hover:opacity-90 transition shadow-glow disabled:opacity-80 disabled:cursor-wait"
          >
            <span className="text-black">{t("matchInput.analyzeButton")}</span>
          </button>
        )}
      </form>

      {selectedHomeTeam && !awayTeamOption && (
        <div className="mt-8 pt-6 border-t border-dark-border">
          <h3 className="text-sm font-semibold text-white mb-1">{t("matchInput.upcomingMatches")}</h3>
          <p className="text-zinc-500 text-xs mb-4">{t("matchInput.clickToFill")}</p>
          {loadingUpcoming ? (
            <p className="text-zinc-500 text-sm">{t("matchInput.loading")}</p>
          ) : upcoming.length === 0 ? (
            <p className="text-zinc-500 text-sm">{t("matchInput.noUpcoming")}</p>
          ) : (
            <ul className="space-y-3">
              {upcoming.map((f, i) => {
                return (
                  <li key={i}>
                    <button
                      type="button"
                      onClick={() => {
                        const homeName = (f.home.name || "").trim();
                        const awayName = (f.away.name || "").trim();
                        if (!homeName || !awayName) return;
                        setHomeTeam(homeName);
                        setAwayTeam(awayName);
                        setSelectedHomeTeam(homeName);
                        setSelectedHomeTeamId(null);
                        setHomeTeamOption({ id: null, name: homeName, crest: f.home.logo ?? null });
                        setAwayTeamOption({ id: null, name: awayName, crest: f.away.logo ?? null });
                      }}
                      className="w-full rounded-xl bg-dark-input/60 border border-dark-border px-3 sm:px-4 py-2.5 text-left transition hover:bg-dark-input hover:border-accent-green/40 cursor-pointer focus:outline-none focus:ring-2 focus:ring-accent-green/50 min-w-0"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
                        <div className="flex-shrink-0 sm:w-32">
                          <div className="text-zinc-400 text-xs sm:text-sm tabular-nums leading-tight">
                            {f.date} <span className="sm:inline">–</span> {f.time}
                          </div>
                          {f.league?.name ? (
                            <div className="text-[11px] text-zinc-500 leading-tight flex items-center gap-1 mt-0.5 min-w-0 overflow-hidden">
                              <span className="text-amber-300 flex-shrink-0">🏆</span>
                              <span className="truncate" title={f.league.name}>
                                {f.league.name}
                              </span>
                            </div>
                          ) : null}
                        </div>
                        <div className="flex items-center gap-2 sm:gap-4 min-w-0 flex-1">
                          <div className="flex items-center gap-1.5 sm:gap-2 min-w-0 flex-1 sm:flex-[0_1_13rem]">
                            {f.home.logo ? (
                              <img src={f.home.logo} alt="" className="w-6 h-6 sm:w-7 sm:h-7 object-contain flex-shrink-0" />
                            ) : (
                              <div className="w-6 h-6 sm:w-7 sm:h-7 rounded-full bg-dark-card flex-shrink-0" />
                            )}
                            <span className="text-white text-xs sm:text-sm font-medium truncate">{f.home.name}</span>
                          </div>
                          <span className="text-zinc-500 text-xs font-medium flex-shrink-0">VS</span>
                          <div className="flex items-center gap-1.5 sm:gap-2 min-w-0 flex-1 sm:flex-[0_1_13rem] justify-end">
                            <span className="text-white text-xs sm:text-sm font-medium truncate text-right">{f.away.name}</span>
                            {f.away.logo ? (
                              <img src={f.away.logo} alt="" className="w-6 h-6 sm:w-7 sm:h-7 object-contain flex-shrink-0" />
                            ) : (
                              <div className="w-6 h-6 sm:w-7 sm:h-7 rounded-full bg-dark-card flex-shrink-0" />
                            )}
                          </div>
                        </div>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
