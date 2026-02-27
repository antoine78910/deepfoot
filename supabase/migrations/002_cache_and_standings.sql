-- Cache 24h + classement (standings) pour analyse de match

-- Equipes: last_updated + stade (venue)
alter table public.teams
  add column if not exists last_updated timestamptz,
  add column if not exists stadium text;

-- H2H: last_updated pour réutiliser si < 24h
alter table public.h2h
  add column if not exists last_updated timestamptz;

-- Classement par ligue/saison (1 requête = toute la ligue)
create table if not exists public.standings (
  league_id int not null,
  season int not null,
  data jsonb not null default '[]',
  last_updated timestamptz not null default now(),
  primary key (league_id, season)
);
create index if not exists idx_standings_league_season on public.standings(league_id, season);

-- RLS (lecture + ecriture pour cache et standings)
alter table public.standings enable row level security;
create policy "Standings read all" on public.standings for select using (true);
create policy "Standings insert all" on public.standings for insert with check (true);
create policy "Standings update all" on public.standings for update using (true);

create policy "Teams insert all" on public.teams for insert with check (true);
create policy "Teams update all" on public.teams for update using (true);
create policy "Results insert all" on public.results for insert with check (true);
create policy "H2H insert all" on public.h2h for insert with check (true);
create policy "H2H update all" on public.h2h for update using (true);
