-- Table players : profils joueurs des ligues (import 1× par saison, stratégie Visifoot).
-- À exécuter une fois dans le SQL Editor Supabase avant sync_players_to_supabase.py.

CREATE TABLE IF NOT EXISTS players (
  id bigint PRIMARY KEY,
  team_id text NOT NULL,
  name text,
  age integer,
  nationality text,
  photo_url text,
  position text,
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE players IS 'Joueurs par équipe/saison (API-Football). Rafraîchi 1× par saison.';
COMMENT ON COLUMN players.id IS 'player_id API-Football';
COMMENT ON COLUMN players.team_id IS 'id équipe API (même valeur que teams.slug)';

CREATE INDEX IF NOT EXISTS idx_players_team_id ON players(team_id);
CREATE INDEX IF NOT EXISTS idx_players_updated_at ON players(updated_at);
