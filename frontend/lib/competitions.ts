export type CompType = "cup" | "league";

export type Competition = {
  id: number;
  name: string;
  region: string;
  season: string;
  type: CompType;
};

export function currentSeasonLabel(): string {
  const y = new Date().getFullYear();
  const m = new Date().getMonth() + 1;
  const start = m >= 8 ? y : y - 1;
  return `${start}/${String(start + 1).slice(-2)}`;
}

/** Année de saison pour l'API (ex: 2025 pour 2025/26). */
export function currentSeasonYear(): number {
  const y = new Date().getFullYear();
  const m = new Date().getMonth() + 1;
  return m >= 8 ? y : y - 1;
}

const BASE: Omit<Competition, "season">[] = [
  // Coupes Europe
  { id: 2, name: "UEFA Champions League", region: "Europe", type: "cup" },
  { id: 3, name: "UEFA Europa League", region: "Europe", type: "cup" },
  { id: 1, name: "World Cup", region: "World", type: "cup" },
  { id: 4, name: "European Championship", region: "Europe", type: "cup" },
  // Ligues (ordre /competitions)
  { id: 266, name: "Botola Pro", region: "Morocco", type: "league" },
  { id: 78, name: "Bundesliga", region: "Germany", type: "league" },
  { id: 88, name: "Eredivisie", region: "Netherlands", type: "league" },
  { id: 144, name: "Jupiler Pro League", region: "Belgium", type: "league" },
  { id: 140, name: "La Liga", region: "Spain", type: "league" },
  { id: 61, name: "Ligue 1", region: "France", type: "league" },
  { id: 62, name: "Ligue 2", region: "France", type: "league" },
  { id: 39, name: "Premier League", region: "England", type: "league" },
  { id: 94, name: "Primeira Liga", region: "Portugal", type: "league" },
  { id: 307, name: "Pro League", region: "Saudi-Arabia", type: "league" },
  { id: 135, name: "Serie A", region: "Italy", type: "league" },
  { id: 207, name: "Super League", region: "Switzerland", type: "league" },
  { id: 203, name: "Süper Lig", region: "Turkey", type: "league" },
  // Autres
  { id: 40, name: "Championship", region: "England", type: "league" },
  { id: 141, name: "Segunda División", region: "Spain", type: "league" },
  { id: 79, name: "2. Bundesliga", region: "Germany", type: "league" },
  { id: 136, name: "Serie B", region: "Italy", type: "league" },
  { id: 41, name: "League One", region: "England", type: "league" },
  { id: 145, name: "Challenger Pro League", region: "Belgium", type: "league" },
  { id: 89, name: "Eerste Divisie", region: "Netherlands", type: "league" },
  { id: 96, name: "Liga Portugal 2", region: "Portugal", type: "league" },
  { id: 204, name: "1. Lig", region: "Turkey", type: "league" },
  { id: 71, name: "Serie A Brasil", region: "Brazil", type: "league" },
];

export function getAllCompetitions(): Competition[] {
  const season = currentSeasonLabel();
  return BASE.map((c) => ({ ...c, season }));
}

export function getCompetitionById(id: number): Competition | null {
  const season = currentSeasonLabel();
  const c = BASE.find((x) => x.id === id);
  return c ? { ...c, season } : null;
}
