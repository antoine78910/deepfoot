-- Separate full analysis count (Starter/Pro/Lifetime) from free analysis count (Free plan)
-- So upgrading from free to starter shows 0/1, not 1/1 from previous free analyses
alter table public.profiles
  add column if not exists full_analyses_used_today int default 0;
alter table public.profiles
  add column if not exists last_full_analysis_date date;
