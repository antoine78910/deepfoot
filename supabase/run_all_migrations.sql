-- Deepfoot — bootstrap schema for a new Supabase project.
-- Paste into SQL Editor (https://supabase.com/dashboard/project/sjhniifpagwxglqjmbgh/sql/new) and Run.

-- ========== tables ==========
create table if not exists public.teams (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text unique not null,
  logo_url text,
  last_updated timestamptz,
  stadium text,
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
  last_updated timestamptz,
  primary key (home_team_id, away_team_id)
);

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  plan text default 'free',
  analyses_used_today int default 0,
  last_analysis_date date,
  updated_at timestamptz default now(),
  analyses_total int default 0,
  subscription_ends_at timestamptz,
  whop_membership_id text,
  chat_requests_used_today int default 0,
  last_chat_date date,
  full_analyses_used_today int default 0,
  last_full_analysis_date date,
  last_full_analysis_at timestamptz,
  last_analysis_at timestamptz
);
alter table public.profiles drop constraint if exists profiles_plan_check;
alter table public.profiles add constraint profiles_plan_check
  check (plan in ('free', 'starter', 'pro', 'lifetime', 'premium'));

create table if not exists public.analysis_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  home_team text not null,
  away_team text not null,
  created_at timestamptz default now()
);
create index if not exists idx_analysis_log_user on analysis_log(user_id, created_at desc);

create table if not exists public.standings (
  league_id int not null,
  season int not null,
  data jsonb not null default '[]',
  last_updated timestamptz not null default now(),
  primary key (league_id, season)
);
create index if not exists idx_standings_league_season on public.standings(league_id, season);

create table if not exists public.analysis_feedback (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  user_id text,
  home_team text,
  away_team text,
  page text default 'analysis',
  email text,
  message text not null
);
create index if not exists idx_analysis_feedback_created_at on public.analysis_feedback(created_at desc);
create index if not exists idx_analysis_feedback_user on public.analysis_feedback(user_id, created_at desc);

create table if not exists public.analysis_events (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  user_id text not null,
  home_team text,
  away_team text,
  source text default 'predict'
);
create index if not exists idx_analysis_events_created_at on public.analysis_events(created_at desc);
create index if not exists idx_analysis_events_user on public.analysis_events(user_id, created_at desc);
create index if not exists idx_analysis_events_match on public.analysis_events(home_team, away_team, created_at desc);

create table if not exists public.analysis_history (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  home_team text not null,
  away_team text not null,
  home_logo text,
  away_logo text,
  league text,
  result jsonb not null,
  created_at timestamptz not null default now()
);
create index if not exists idx_analysis_history_user_created on public.analysis_history(user_id, created_at desc);

-- ========== RLS ==========
alter table public.teams enable row level security;
alter table public.results enable row level security;
alter table public.h2h enable row level security;
alter table public.profiles enable row level security;
alter table public.analysis_log enable row level security;
alter table public.standings enable row level security;
alter table public.analysis_history enable row level security;

drop policy if exists "Teams read all" on public.teams;
create policy "Teams read all" on public.teams for select using (true);
drop policy if exists "Teams insert all" on public.teams;
create policy "Teams insert all" on public.teams for insert with check (true);
drop policy if exists "Teams update all" on public.teams;
create policy "Teams update all" on public.teams for update using (true);

drop policy if exists "Results read all" on public.results;
create policy "Results read all" on public.results for select using (true);
drop policy if exists "Results insert all" on public.results;
create policy "Results insert all" on public.results for insert with check (true);

drop policy if exists "H2H read all" on public.h2h;
create policy "H2H read all" on public.h2h for select using (true);
drop policy if exists "H2H insert all" on public.h2h;
create policy "H2H insert all" on public.h2h for insert with check (true);
drop policy if exists "H2H update all" on public.h2h;
create policy "H2H update all" on public.h2h for update using (true);

drop policy if exists "Profiles own" on public.profiles;
drop policy if exists "Profiles select own" on public.profiles;
drop policy if exists "Profiles insert own" on public.profiles;
drop policy if exists "Profiles update own" on public.profiles;
drop policy if exists "Profiles delete own" on public.profiles;
create policy "Profiles select own" on public.profiles for select using (auth.uid() = id);
create policy "Profiles insert own" on public.profiles for insert with check (auth.uid() = id);
create policy "Profiles update own" on public.profiles for update using (auth.uid() = id) with check (auth.uid() = id);
create policy "Profiles delete own" on public.profiles for delete using (auth.uid() = id);

drop policy if exists "Analysis log own" on public.analysis_log;
create policy "Analysis log own" on public.analysis_log for select using (auth.uid() = user_id);
drop policy if exists "Analysis log insert" on public.analysis_log;
create policy "Analysis log insert" on public.analysis_log for insert with check (auth.uid() = user_id);

drop policy if exists "Standings read all" on public.standings;
create policy "Standings read all" on public.standings for select using (true);
drop policy if exists "Standings insert all" on public.standings;
create policy "Standings insert all" on public.standings for insert with check (true);
drop policy if exists "Standings update all" on public.standings;
create policy "Standings update all" on public.standings for update using (true);

drop policy if exists "Users can read own analysis history" on public.analysis_history;
create policy "Users can read own analysis history"
  on public.analysis_history for select using (auth.uid() = user_id);
drop policy if exists "Users can insert own analysis history" on public.analysis_history;
create policy "Users can insert own analysis history"
  on public.analysis_history for insert with check (auth.uid() = user_id);
drop policy if exists "Users can delete own analysis history" on public.analysis_history;
create policy "Users can delete own analysis history"
  on public.analysis_history for delete using (auth.uid() = user_id);

-- ========== auto-create profile on Google / email signup ==========
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, plan)
  values (new.id, 'free')
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
