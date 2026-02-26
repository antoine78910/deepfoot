"use client";

import { useState, useEffect, useRef, useCallback } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type TeamOption = { id: number | string | null; name: string; crest: string | null };

interface TeamAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  disabled?: boolean;
  className?: string;
}

const DEBOUNCE_MS = 280;
const MIN_QUERY_LENGTH = 1;

export function TeamAutocomplete({
  value,
  onChange,
  placeholder,
  disabled,
  className = "",
}: TeamAutocompleteProps) {
  const [query, setQuery] = useState(value);
  const [options, setOptions] = useState<TeamOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const fetchTeams = useCallback(async (q: string) => {
    if (!q.trim()) {
      setOptions([]);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(
        `${API_URL}/teams?q=${encodeURIComponent(q.trim())}&limit=15`
      );
      const data = await res.json();
      setOptions(data.teams || []);
      setHighlight(-1);
    } catch {
      setOptions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setQuery(value);
  }, [value]);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.length < MIN_QUERY_LENGTH) {
      setOptions([]);
      setOpen(false);
      return;
    }
    debounceRef.current = setTimeout(() => {
      fetchTeams(query);
      setOpen(true);
    }, DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, fetchTeams]);

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
    onChange(team.name);
    setQuery(team.name);
    setOpen(false);
    setOptions([]);
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
          type="text"
          placeholder={placeholder}
          value={query}
          onChange={handleInputChange}
          onFocus={() => query.length >= MIN_QUERY_LENGTH && options.length > 0 && setOpen(true)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          autoComplete="off"
          aria-autocomplete="list"
          aria-expanded={open}
        />
      </div>
      {open && (options.length > 0 || loading) && (
        <ul
          className="absolute z-50 w-full mt-1 rounded-xl bg-dark-card border border-dark-border shadow-glow max-h-64 overflow-y-auto"
          role="listbox"
        >
          {loading ? (
            <li className="px-4 py-3 text-zinc-400 text-sm">Chargement…</li>
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
                <span className="text-white font-medium truncate">{team.name}</span>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
