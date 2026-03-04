-- Tables for storing scraped news and motivation analysis per match (DeepFoot).
-- Run in Supabase SQL Editor.

-- Scraped news items (one row per article/snippet)
CREATE TABLE IF NOT EXISTS analysis_news (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  home_team TEXT NOT NULL,
  away_team TEXT NOT NULL,
  league TEXT DEFAULT '',
  source TEXT DEFAULT '',
  title TEXT DEFAULT '',
  snippet TEXT DEFAULT '',
  url TEXT DEFAULT '',
  keywords_found JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_analysis_news_match ON analysis_news (home_team, away_team);
CREATE INDEX IF NOT EXISTS idx_analysis_news_created ON analysis_news (created_at DESC);

-- Motivation analysis (one row per analysis; full GPT output)
CREATE TABLE IF NOT EXISTS analysis_motivation (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  home_team TEXT NOT NULL,
  away_team TEXT NOT NULL,
  league TEXT DEFAULT '',
  analysis_text TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_analysis_motivation_match ON analysis_motivation (home_team, away_team);
CREATE INDEX IF NOT EXISTS idx_analysis_motivation_created ON analysis_motivation (created_at DESC);

-- RLS: enable and allow backend (anon key) to insert/select.
ALTER TABLE analysis_news ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_motivation ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow insert analysis_news" ON analysis_news;
DROP POLICY IF EXISTS "Allow select analysis_news" ON analysis_news;
CREATE POLICY "Allow insert analysis_news" ON analysis_news FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow select analysis_news" ON analysis_news FOR SELECT USING (true);

DROP POLICY IF EXISTS "Allow insert analysis_motivation" ON analysis_motivation;
DROP POLICY IF EXISTS "Allow select analysis_motivation" ON analysis_motivation;
CREATE POLICY "Allow insert analysis_motivation" ON analysis_motivation FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow select analysis_motivation" ON analysis_motivation FOR SELECT USING (true);
