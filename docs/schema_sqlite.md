# Schéma de données SQLite — Suivi de patrimoine

## Vue d'ensemble

- **Actifs** : table centrale `actifs` avec un `type`, et des tables de détail par type (ticker, immobilier).
- **Emprunts** : table dédiée, liée optionnellement à un bien immobilier.
- **Historique / Positions** : conservés pour les séries temporelles (valeur et quantités).

Les types d'actifs sont : `action`, `crypto`, `livret`, `immobilier`, `fonds_euro`.

---

## Schéma SQL

```sql
-- =============================================================================
-- ACTIFS (table centrale)
-- =============================================================================
-- Un enregistrement par actif. Les colonnes communes à tous les types.
-- Pour les champs spécifiques (ticker, immobilier), voir les tables de détail.
CREATE TABLE actifs (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL CHECK(type IN ('action', 'crypto', 'livret', 'immobilier', 'fonds_euro')),
  nom TEXT NOT NULL,
  montant_actuel REAL NOT NULL DEFAULT 0,
  courtier TEXT,
  enveloppe TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_actifs_type ON actifs(type);


-- =============================================================================
-- Détail des actifs à prix de marché (actions, crypto)
-- =============================================================================
CREATE TABLE actifs_ticker (
  actif_id TEXT PRIMARY KEY REFERENCES actifs(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  quantite REAL NOT NULL DEFAULT 0,
  pru REAL NOT NULL DEFAULT 0
);


-- =============================================================================
-- EMPRUNTS (avant actifs_immobilier pour la FK)
-- =============================================================================
CREATE TABLE emprunts (
  id TEXT PRIMARY KEY,
  nom TEXT NOT NULL,
  montant_emprunte REAL NOT NULL,
  taux_annuel REAL NOT NULL,
  mensualite REAL NOT NULL,
  duree_mois INTEGER NOT NULL,
  date_debut TEXT NOT NULL,
  date_fin TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

-- date_fin peut être dérivée (date_debut + duree_mois) ou stockée pour suivi
-- Le capital restant dû est calculé à l'affichage (jamais stocké).


-- =============================================================================
-- Détail des actifs immobiliers
-- =============================================================================
CREATE TABLE actifs_immobilier (
  actif_id TEXT PRIMARY KEY REFERENCES actifs(id) ON DELETE CASCADE,
  prix_achat REAL NOT NULL,
  emprunt_id TEXT REFERENCES emprunts(id) ON DELETE SET NULL,
  type_bien TEXT NOT NULL,
  adresse TEXT,
  superficie_m2 REAL,
  notes TEXT
);

CREATE INDEX idx_actifs_immobilier_emprunt ON actifs_immobilier(emprunt_id);


-- =============================================================================
-- HISTORIQUE (valeurs passées par actif)
-- =============================================================================
CREATE TABLE historique (
  asset_id TEXT NOT NULL REFERENCES actifs(id) ON DELETE CASCADE,
  date TEXT NOT NULL,
  montant REAL NOT NULL,
  PRIMARY KEY (asset_id, date)
);

CREATE INDEX idx_historique_date ON historique(date);


-- =============================================================================
-- POSITIONS (quantités passées pour actifs ticker)
-- =============================================================================
CREATE TABLE positions (
  asset_id TEXT NOT NULL REFERENCES actifs(id) ON DELETE CASCADE,
  date TEXT NOT NULL,
  quantite REAL NOT NULL,
  PRIMARY KEY (asset_id, date)
);

CREATE INDEX idx_positions_date ON positions(date);


-- =============================================================================
-- Référentiel (courtiers / enveloppes) — optionnel, pour listes déroulantes
-- =============================================================================
CREATE TABLE referentiel (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kind TEXT NOT NULL CHECK(kind IN ('courtier', 'enveloppe')),
  value TEXT NOT NULL,
  UNIQUE(kind, value)
);
```

---

## Règles métier

| Table              | Règle |
|--------------------|--------|
| `actifs`           | `type` détermine quelles tables de détail sont remplies. Pour `action` et `crypto` → une ligne dans `actifs_ticker`. Pour `immobilier` → une ligne dans `actifs_immobilier`. |
| `actifs_immobilier`| `emprunt_id` optionnel : un bien peut avoir 0 ou 1 emprunt associé. |
| `emprunts`         | Peuvent exister sans bien immobilier (prêt à la conso, etc.). Le capital restant dû est calculé à l’affichage (formule d’amortissement). |
| `historique`       | Une ligne par (asset_id, date) pour l’évolution de la valeur. |
| `positions`        | Une ligne par (asset_id, date) pour l’évolution des quantités (actifs ticker). |

---

## Correspondance avec l’existant (CSV)

| Ancien (patrimoine.csv) | Nouveau |
|------------------------|--------|
| `id`                   | `actifs.id` |
| `nom`                  | `actifs.nom` |
| `categorie`            | `actifs.type` (mapper Actions & Fonds → action, etc.) |
| `montant`              | `actifs.montant_actuel` |
| `ticker`, `quantite`, `pru` | `actifs_ticker` (si type = action ou crypto) |
| `courtier`, `enveloppe`| `actifs.courtier`, `actifs.enveloppe` |
| —                      | Immobilier : `actifs_immobilier` (prix_achat, type_bien, adresse, superficie_m2, emprunt_id) |
| —                      | Emprunts : table `emprunts` |

---

## Exemples de requêtes utiles

**Tous les actifs avec détail ticker (actions/crypto) :**
```sql
SELECT a.*, t.ticker, t.quantite, t.pru
FROM actifs a
LEFT JOIN actifs_ticker t ON t.actif_id = a.id
WHERE a.type IN ('action', 'crypto');
```

**Biens immobiliers avec leur emprunt :**
```sql
SELECT a.*, i.prix_achat, i.type_bien, i.adresse, i.superficie_m2,
       e.montant_emprunte, e.taux_annuel, e.mensualite, e.duree_mois
FROM actifs a
JOIN actifs_immobilier i ON i.actif_id = a.id
LEFT JOIN emprunts e ON e.id = i.emprunt_id;
```

**Total par type d’actif :**
```sql
SELECT type, SUM(montant_actuel) AS total
FROM actifs
GROUP BY type;
```

**Total patrimoine (actifs) :**
```sql
SELECT SUM(montant_actuel) FROM actifs;
```

**Patrimoine net (actifs − encours emprunts) :** calculé dans l’app (`get_total_emprunts()` qui dérive le capital restant dû pour chaque emprunt, puis total actifs − ce total).

---

## Types de biens immobiliers (suggestion)

Valeurs possibles pour `actifs_immobilier.type_bien` :
- `appartement`
- `maison`
- `terrain`
- `local_commercial`
- `autre`

À définir dans les constantes ou dans une table de référence si besoin.

---

## Mapping catégorie (actuel) → type (SQLite)

| Catégorie actuelle (CSV) | type SQLite   |
|--------------------------|---------------|
| Actions & Fonds          | `action`      |
| Crypto                   | `crypto`      |
| Livrets                  | `livret`      |
| Immobilier               | `immobilier`  |
| Fonds euros              | `fonds_euro`  |

---

## Schéma relationnel (résumé)

```
actifs (id, type, nom, montant_actuel, courtier, enveloppe)
   │
   ├── 1:1 actifs_ticker (actif_id, ticker, quantite, pru)     [type in ('action','crypto')]
   │
   └── 1:1 actifs_immobilier (actif_id, prix_achat, emprunt_id, type_bien, adresse, superficie_m2)
              │
              └── N:1 emprunts (id, nom, montant_emprunte, taux_annuel, mensualite, duree_mois, date_debut, ...)

historique (asset_id → actifs.id, date, montant)
positions  (asset_id → actifs.id, date, quantite)
referentiel (kind, value)
```
