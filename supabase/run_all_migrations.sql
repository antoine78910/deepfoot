-- Visifoot 2.0 - Schema complet (001 + 002). A executer en une fois dans le SQL Editor Supabase.

-- ========== 001_initial ==========
create table if not exists public.teams (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text unique not null,
  logo_url text,
  created_at timestamptz default now()
);

create table if not exists public.results (
  id uuid primary key default gen_random_uuid(),
  home_team_id text not null,
  away_team_id text not null,
  home_goals int not null,
  away_goals int not null,
  date date not null,
  league text,
  created_at timestamptz default now()
);
create index if not exists idx_results_home on results(home_team_id, date desc);
create index if not exists idx_results_away on results(away_team_id, date desc);

create table if not exists public.h2h (
  home_team_id text not null,
  away_team_id text not null,
  home_wins int default 0,
  draws int default 0,
  away_wins int default 0,
  primary key (home_team_id, away_team_id)
);

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  plan text default 'free' check (plan in ('free', 'premium')),
  analyses_used_today int default 0,
  last_analysis_date date,
  updated_at timestamptz default now()
);

create table if not exists public.analysis_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  home_team text not null,
  away_team text not null,
  created_at timestamptz default now()
);
create index if not exists idx_analysis_log_user on analysis_log(user_id, created_at desc);

alter table public.teams enable row level security;
alter table public.results enable row level security;
alter table public.h2h enable row level security;
alter table public.profiles enable row level security;
alter table public.analysis_log enable row level security;

create policy "Teams read all" on public.teams for select using (true);
create policy "Results read all" on public.results for select using (true);
create policy "H2H read all" on public.h2h for select using (true);
create policy "Profiles own" on public.profiles for all using (auth.uid() = id);
create policy "Analysis log own" on public.analysis_log for select using (auth.uid() = user_id);
create policy "Analysis log insert" on public.analysis_log for insert with check (auth.uid() = user_id);

-- ========== 002_cache_and_standings ==========
alter table public.teams
  add column if not exists last_updated timestamptz,
  add column if not exists stadium text;

alter table public.h2h
  add column if not exists last_updated timestamptz;

create table if not exists public.standings (
  league_id int not null,
  season int not null,
  data jsonb not null default '[]',
  last_updated timestamptz not null default now(),
  primary key (league_id, season)
);
create index if not exists idx_standings_league_season on public.standings(league_id, season);

alter table public.standings enable row level security;
create policy "Standings read all" on public.standings for select using (true);
create policy "Standings insert all" on public.standings for insert with check (true);
create policy "Standings update all" on public.standings for update using (true);

create policy "Teams insert all" on public.teams for insert with check (true);
create policy "Teams update all" on public.teams for update using (true);
create policy "Results insert all" on public.results for insert with check (true);
create policy "H2H insert all" on public.h2h for insert with check (true);
create policy "H2H update all" on public.h2h for update using (true);
