"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useLanguage } from "@/contexts/LanguageContext";
import { useAppBasePath } from "@/contexts/AppBasePathContext";

import { getAllCompetitions } from "@/lib/competitions";

const LOGO_BASE = "https://media.api-sports.io/football/leagues";

function TrophyIcon() {
  return (
    <svg className="w-5 h-5 text-zinc-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7" />
    </svg>
  );
}

function GlobeIcon() {
  return (
    <svg className="w-5 h-5 text-zinc-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0h.5a2.5 2.5 0 002.5-2.5V3.935M12 12a2 2 0 104 0 2 2 0 00-4 0zM3 20v-2.945a2 2 0 01.055-.055" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg className="w-5 h-5 text-zinc-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  );
}

function ChevronIcon() {
  return (
    <svg className="w-5 h-5 text-zinc-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  );
}

export default function CompetitionsPage() {
  const { t } = useLanguage();
  const basePath = useAppBasePath();
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const list = getAllCompetitions();
    if (!q) return list;
    return list.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.region.toLowerCase().includes(q)
    );
  }, [search]);

  const cups = filtered.filter((c) => c.type === "cup");
  const leagues = filtered.filter((c) => c.type === "league");

  return (
    <div className="p-8 w-full flex flex-col items-center">
      <div className="w-full max-w-xl mx-auto">
        <h1 className="text-2xl font-bold text-white text-center">{t("competitions.title")}</h1>
        <p className="text-zinc-400 mt-1 text-center">{t("competitions.subtitle")}</p>
        <p className="text-zinc-500 text-sm mt-3 text-center max-w-lg mx-auto">
          {t("competitions.description")}
        </p>

        <div className="mt-6">
          <div className="relative rounded-xl border border-dark-border bg-dark-input/40 focus-within:border-accent-green/50 transition-colors">
            <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
              <SearchIcon />
            </div>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("competitions.searchPlaceholder")}
              className="w-full pl-12 pr-4 py-3 bg-transparent text-white placeholder-zinc-500 rounded-xl focus:outline-none"
            />
          </div>
        </div>

        <div className="mt-8 space-y-8">
          {cups.length > 0 && (
            <section>
              <div className="flex items-center gap-2 mb-4">
                <TrophyIcon />
                <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
                  {t("competitions.cups")}
                </h2>
              </div>
              <ul className="space-y-3">
                {cups.map((c) => (
                  <li key={c.id}>
                    <Link
                      href={`${basePath}/competitions/${c.id}`}
                      className="w-full flex items-center gap-4 rounded-xl bg-dark-card border border-dark-border px-4 py-3 text-left transition hover:bg-dark-input/60 hover:border-accent-green/40 cursor-pointer focus:outline-none focus:ring-2 focus:ring-accent-green/50 block"
                    >
                      <img
                        src={`${LOGO_BASE}/${c.id}.png`}
                        alt=""
                        className="w-10 h-10 object-contain flex-shrink-0 bg-white/5 rounded"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-white font-medium truncate">{c.name}</p>
                        <p className="text-zinc-500 text-sm">
                          {c.region}
                          <span className="inline-block w-1.5 h-1.5 rounded-full bg-zinc-500 mx-2 align-middle" />
                          {c.season}
                        </p>
                      </div>
                      <ChevronIcon />
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {leagues.length > 0 && (
            <section>
              <div className="flex items-center gap-2 mb-4">
                <GlobeIcon />
                <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
                  {t("competitions.leagues")}
                </h2>
              </div>
              <ul className="space-y-3">
                {leagues.map((c) => (
                  <li key={c.id}>
                    <Link
                      href={`${basePath}/competitions/${c.id}`}
                      className="w-full flex items-center gap-4 rounded-xl bg-dark-card border border-dark-border px-4 py-3 text-left transition hover:bg-dark-input/60 hover:border-accent-green/40 cursor-pointer focus:outline-none focus:ring-2 focus:ring-accent-green/50 block"
                    >
                      <img
                        src={`${LOGO_BASE}/${c.id}.png`}
                        alt=""
                        className="w-10 h-10 object-contain flex-shrink-0 bg-white/5 rounded"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-white font-medium truncate">{c.name}</p>
                        <p className="text-zinc-500 text-sm">
                          {c.region}
                          <span className="inline-block w-1.5 h-1.5 rounded-full bg-zinc-500 mx-2 align-middle" />
                          {c.season}
                        </p>
                      </div>
                      <ChevronIcon />
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {filtered.length === 0 && (
            <p className="text-zinc-500 text-center py-8">{t("competitions.noResults")}</p>
          )}
        </div>
      </div>
    </div>
  );
}
