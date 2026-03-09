-- Timestamp of last analysis use (for 24h countdown per user when limit reached)
alter table public.profiles
  add column if not exists last_full_analysis_at timestamptz;
alter table public.profiles
  add column if not exists last_analysis_at timestamptz;
