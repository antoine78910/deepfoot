-- Ajoute la colonne search_terms à la table teams pour la recherche rapide (recherche magique).
-- À exécuter une fois dans le SQL Editor Supabase avant de lancer les scripts de sync.

ALTER TABLE teams ADD COLUMN IF NOT EXISTS search_terms text;
ALTER TABLE teams ADD COLUMN IF NOT EXISTS country text;

-- Remplir la table avec toutes les équipes (clubs + sélections nationales) et leurs blasons :
--   cd backend && .\venv\Scripts\python.exe scripts/sync_teams_by_country_to_supabase.py
-- (GET /teams?country={Pays} → inclut France, Spain, Brazil, etc. et tous les clubs du pays)
-- Alternative par ligues uniquement : scripts/sync_teams_to_supabase.py

-- Optionnel : index pour accélérer les recherches ilike (PostgreSQL)
-- CREATE INDEX IF NOT EXISTS idx_teams_search_terms ON teams USING gin (search_terms gin_trgm_ops);
-- (nécessite l'extension pg_trgm : CREATE EXTENSION IF NOT EXISTS pg_trgm;)
