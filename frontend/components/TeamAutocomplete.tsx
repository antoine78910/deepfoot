"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { getApiUrl } from "@/lib/api";

export type TeamOption = { id: number | string | null; name: string; crest: string | null; country?: string | null };

interface TeamAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  onSelect?: (team: TeamOption) => void;
  placeholder: string;
  disabled?: boolean;
  className?: string;
  /** Debounce ms before fetching (default 0 = LP strategy). */
  debounceMs?: number;
  /** Max teams to request from API (default 20 = LP strategy). */
  fetchLimit?: number;
  /** Preload cache size (default 200 = LP strategy, fast). Use higher only if needed. */
  preloadLimit?: number;
  /** When true, never show the suggestions dropdown (e.g. team already chosen from upcoming match). */
  suppressSuggestions?: boolean;
}
const MIN_QUERY_LENGTH = 2;
const MIN_NETWORK_QUERY_LENGTH = 2;
const LOCAL_CACHE_KEY = "df:teams:autocomplete:v1";
const LOCAL_CACHE_TTL_MS = 24 * 60 * 60 * 1000;
const INSTANT_RESULTS_ENOUGH = 8;

// Alias pour filtre client instantané (même logique que le backend)
const CLIENT_ALIASES: Record<string, string[]> = {
  aja: ["auxerre"],
  psg: ["paris"],
  psj: ["paris"],
  om: ["marseille"],
  ol: ["lyon", "olympique"],
  ogc: ["nice"],
  rcs: ["strasbourg"],
  scc: ["lens"],
  losc: ["lille"],
  monaco: ["monaco"],
  rennes: ["rennes"],
  lorient: ["lorient"],
  brest: ["brest"],
  nantes: ["nantes"],
  reims: ["reims"],
  lens: ["lens"],
  tfc: ["toulouse"],
  clermont: ["clermont"],
};

function normalize(s: string): string {
  return s
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function teamMatchesQuery(team: TeamOption, q: string): boolean {
  const n = normalize(team.name);
  const qn = normalize(q);
  if (!qn) return true;
  const words = n.split(/\s+/g).filter(Boolean);
  if (n.startsWith(qn) || words.some((w) => w.startsWith(qn))) return true;
  const expanded = CLIENT_ALIASES[qn];
  if (!expanded) return false;
  return expanded.some((term) => n.startsWith(term) || words.some((w) => w.startsWith(term)));
}

const DEFAULT_DEBOUNCE_MS = 0;
const DEFAULT_PRELOAD_LIMIT = 200;

function readTeamsFromLocalCache(): TeamOption[] {
  try {
    if (typeof window === "undefined") return [];
    const raw = window.localStorage.getItem(LOCAL_CACHE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as { ts?: number; teams?: TeamOption[] };
    if (!parsed?.ts || !Array.isArray(parsed?.teams)) return [];
    if (Date.now() - parsed.ts > LOCAL_CACHE_TTL_MS) return [];
    return parsed.teams.filter((t) => Boolean(t?.id) && Boolean(t?.crest));
  } catch {
    return [];
  }
}

function writeTeamsToLocalCache(teams: TeamOption[]) {
  try {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(LOCAL_CACHE_KEY, JSON.stringify({ ts: Date.now(), teams }));
  } catch {
    // Ignore storage quota/private mode failures.
  }
}

export function TeamAutocomplete({
  value,
  onChange,
  onSelect,
  placeholder,
  disabled,
  className = "",
  debounceMs = DEFAULT_DEBOUNCE_MS,
  fetchLimit = 20,
  preloadLimit = DEFAULT_PRELOAD_LIMIT,
  suppressSuggestions = false,
}: TeamAutocompleteProps) {
  const [query, setQuery] = useState(value);
  const [options, setOptions] = useState<TeamOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reqIdRef = useRef(0);
  const cacheRef = useRef<Map<string, TeamOption[]>>(new Map());
  const warmTeamsRef = useRef<TeamOption[]>([]);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const justSelectedRef = useRef(false);
  const mountedRef = useRef(true);

  const fetchTeams = useCallback(async (q: string) => {
    const qTrim = q.trim();
    if (!qTrim) {
      if (mountedRef.current) {
        setOptions([]);
        setLoading(false);
      }
      return;
    }
    if (qTrim.length < MIN_NETWORK_QUERY_LENGTH) {
      if (mountedRef.current) setLoading(false);
      return;
    }
    const qNormalized = normalize(qTrim);
    const cached = cacheRef.current.get(qNormalized);
    if (cached) {
      if (mountedRef.current) {
        setOptions(cached.slice(0, 20));
        setLoading(false);
      }
      return;
    }
    const reqId = ++reqIdRef.current;
    if (mountedRef.current) setLoading(true);
    try {
      let data: { teams?: TeamOption[] } = {};
      try {
        const res = await fetch(
          `${getApiUrl()}/teams?q=${encodeURIComponent(qTrim)}&limit=${fetchLimit}`,
          {}
        );
        if (!res.ok) {
          if (mountedRef.current && reqId === reqIdRef.current) setOptions([]);
          return;
        }
        data = await res.json();
      } catch (err) {
        if (mountedRef.current && reqId === reqIdRef.current) setOptions([]);
        return;
      }
      if (reqId !== reqIdRef.current) return;
      const apiTeams = (data.teams || [])
        .filter((t: TeamOption) => Boolean(t?.name))
        .filter((t: TeamOption) => teamMatchesQuery(t, qTrim));
      cacheRef.current.set(qNormalized, apiTeams);
      if (mountedRef.current) {
        setOptions(apiTeams.slice(0, 20));
        setHighlight(-1);
      }
    } catch {
      if (reqId !== reqIdRef.current) return;
      if (mountedRef.current) setOptions([]);
    } finally {
      if (mountedRef.current && reqId === reqIdRef.current) setLoading(false);
    }
  }, [fetchLimit]);

  useEffect(() => {
    let cancelled = false;
    mountedRef.current = true;
    const cached = readTeamsFromLocalCache();
    if (cached.length > 0) {
      warmTeamsRef.current = cached;
    }
    const preload = async () => {
      try {
        const res = await fetch(`${getApiUrl()}/teams?limit=${preloadLimit}`);
        if (!res.ok) return;
        const data = await res.json();
        if (cancelled) return;
        const teams = (data.teams || [])
          .filter((t: TeamOption) => Boolean(t?.name));
        warmTeamsRef.current = teams;
        writeTeamsToLocalCache(teams);
      } catch {
        // Silent fallback: autocomplete keeps network mode only.
      }
    };
    void preload();
    return () => {
      cancelled = true;
      mountedRef.current = false;
    };
  }, [preloadLimit]);

  useEffect(() => {
    setQuery(value);
  }, [value]);

  useEffect(() => {
    if (suppressSuggestions) setOpen(false);
  }, [suppressSuggestions]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.length < MIN_QUERY_LENGTH) {
      setOptions([]);
      setOpen(false);
      setLoading(false);
      return;
    }
    const q = query.trim();
    let instantCount = 0;
    if (q) {
      const instant = warmTeamsRef.current
        .filter((t) => teamMatchesQuery(t, q))
        .slice(0, 20);
      instantCount = instant.length;
      if (instant.length > 0) {
        setOptions(instant);
        setHighlight(-1);
        if (!suppressSuggestions) setOpen(true);
      }
    }
    debounceRef.current = setTimeout(() => {
      if (justSelectedRef.current) {
        justSelectedRef.current = false;
        return;
      }
      // Offline-first: if local preload already gives enough relevant teams,
      // skip network for a snappier UX.
      if (q.length < MIN_NETWORK_QUERY_LENGTH || instantCount >= INSTANT_RESULTS_ENOUGH) {
        setLoading(false);
        return;
      }
      void fetchTeams(query);
      if (!suppressSuggestions) setOpen(true);
    }, debounceMs);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      // Don't abort here: the next fetchTeams() will abort the previous request.
      // Aborting in cleanup can trigger AbortError in the catch path.
    };
  }, [query, fetchTeams, debounceMs, suppressSuggestions]);

  const onFocus = useCallback(() => {
    if (!suppressSuggestions && query.length >= MIN_QUERY_LENGTH && options.length > 0) setOpen(true);
  }, [query.length, options.length, suppressSuggestions]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
    onChange(e.target.value);
  };

  const handleSelect = (team: TeamOption) => {
    justSelectedRef.current = true;
    onChange(team.name);
    onSelect?.(team);
    setQuery(team.name);
    setOpen(false);
    setOptions([]);
    inputRef.current?.blur();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open || options.length === 0) {
      if (e.key === "Escape") setOpen(false);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlight((h) => (h < options.length - 1 ? h + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => (h > 0 ? h - 1 : options.length - 1));
    } else if (e.key === "Enter" && highlight >= 0 && options[highlight]) {
      e.preventDefault();
      handleSelect(options[highlight]);
    } else if (e.key === "Escape") {
      setOpen(false);
      setHighlight(-1);
    }
  };

  return (
    <div ref={wrapperRef} className={`relative ${className}`}>
      <div className="input-gradient-border">
        <input
          ref={inputRef}
          type="text"
          name="team"
          placeholder={placeholder}
          value={query}
          onChange={handleInputChange}
          onFocus={onFocus}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          autoComplete="off"
          data-1p-ignore
          data-lpignore="true"
          data-form-type="other"
          aria-autocomplete="list"
          aria-expanded={open}
        />
      </div>
      {!suppressSuggestions && open && (options.length > 0 || loading) && (
        <ul
          className="absolute z-50 w-full mt-1 rounded-xl bg-dark-card border border-dark-border shadow-glow max-h-64 overflow-y-auto"
          role="listbox"
        >
          {loading && options.length === 0 ? (
            <li className="px-4 py-4 flex items-center justify-center gap-2 text-zinc-400 text-sm">
              <svg className="animate-spin w-5 h-5 text-accent-cyan" fill="none" viewBox="0 0 24 24" aria-hidden>
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span>Chargement…</span>
            </li>
          ) : (
            options.map((team, i) => (
              <li
                key={team.id ?? team.name ?? i}
                role="option"
                aria-selected={highlight === i}
                className={`flex items-center gap-3 px-4 py-2.5 cursor-pointer transition ${
                  highlight === i ? "bg-dark-input" : "hover:bg-dark-input/80"
                }`}
                onMouseEnter={() => setHighlight(i)}
                onMouseDown={(e) => {
                  e.preventDefault();
                  handleSelect(team);
                }}
              >
                {team.crest ? (
                  <img
                    src={team.crest}
                    alt=""
                    className="w-8 h-8 object-contain flex-shrink-0"
                  />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-dark-input flex-shrink-0 flex items-center justify-center text-zinc-500 text-xs">
                    ?
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <span className="text-white font-medium truncate block">{team.name}</span>
                  {team.country ? (
                    <span className="text-xs text-zinc-500 truncate block">{team.country}</span>
                  ) : null}
                </div>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
