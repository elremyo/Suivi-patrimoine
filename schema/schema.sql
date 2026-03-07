-- Schéma SQLite — Suivi de patrimoine
-- Exécutable avec: sqlite3 data/patrimoine.db < schema/schema.sql

-- =============================================================================
-- ACTIFS (table centrale)
-- =============================================================================
CREATE TABLE IF NOT EXISTS actifs (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL CHECK(type IN ('action', 'crypto', 'livret', 'immobilier', 'fonds_euro')),
  nom TEXT NOT NULL,
  montant_actuel REAL NOT NULL DEFAULT 0,
  courtier TEXT,
  enveloppe TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_actifs_type ON actifs(type);


-- =============================================================================
-- Détail des actifs à prix de marché (actions, crypto)
-- =============================================================================
CREATE TABLE IF NOT EXISTS actifs_ticker (
  actif_id TEXT PRIMARY KEY REFERENCES actifs(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  quantite REAL NOT NULL DEFAULT 0,
  pru REAL NOT NULL DEFAULT 0
);


-- =============================================================================
-- EMPRUNTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS emprunts (
  id TEXT PRIMARY KEY,
  nom TEXT NOT NULL,
  montant_emprunte REAL NOT NULL,
  taux_annuel REAL NOT NULL,
  mensualite REAL NOT NULL,
  duree_mois INTEGER NOT NULL,
  date_debut TEXT NOT NULL,
  date_fin TEXT,
  capital_restant_du REAL,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);


-- =============================================================================
-- Détail des actifs immobiliers
-- =============================================================================
CREATE TABLE IF NOT EXISTS actifs_immobilier (
  actif_id TEXT PRIMARY KEY REFERENCES actifs(id) ON DELETE CASCADE,
  prix_achat REAL NOT NULL,
  emprunt_id TEXT REFERENCES emprunts(id) ON DELETE SET NULL,
  type_bien TEXT NOT NULL,
  adresse TEXT,
  superficie_m2 REAL,
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_actifs_immobilier_emprunt ON actifs_immobilier(emprunt_id);


-- =============================================================================
-- HISTORIQUE (valeurs passées par actif)
-- =============================================================================
CREATE TABLE IF NOT EXISTS historique (
  asset_id TEXT NOT NULL REFERENCES actifs(id) ON DELETE CASCADE,
  date TEXT NOT NULL,
  montant REAL NOT NULL,
  PRIMARY KEY (asset_id, date)
);

CREATE INDEX IF NOT EXISTS idx_historique_date ON historique(date);
CREATE INDEX IF NOT EXISTS idx_historique_asset ON historique(asset_id);


-- =============================================================================
-- POSITIONS (quantités passées pour actifs ticker)
-- =============================================================================
CREATE TABLE IF NOT EXISTS positions (
  asset_id TEXT NOT NULL REFERENCES actifs(id) ON DELETE CASCADE,
  date TEXT NOT NULL,
  quantite REAL NOT NULL,
  PRIMARY KEY (asset_id, date)
);

CREATE INDEX IF NOT EXISTS idx_positions_date ON positions(date);
CREATE INDEX IF NOT EXISTS idx_positions_asset ON positions(asset_id);


-- =============================================================================
-- Référentiel (courtiers / enveloppes)
-- =============================================================================
CREATE TABLE IF NOT EXISTS referentiel (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL CHECK(kind IN ('courtier', 'enveloppe')),
  value TEXT NOT NULL,
  UNIQUE(kind, value)
);
