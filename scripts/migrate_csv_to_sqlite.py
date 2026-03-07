#!/usr/bin/env python3
"""
Migration CSV → SQLite

Lit les fichiers data/patrimoine.csv, data/historique.csv, data/positions.csv
et data/referentiel.csv (si présent) puis remplit la base data/patrimoine.db.

Usage (depuis la racine du projet) :
    python scripts/migrate_csv_to_sqlite.py

L'application utilise par défaut la base SQLite (data/patrimoine.db).
"""

import os
import sys
from pathlib import Path

# Racine du projet
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import pandas as pd
from pandas.errors import EmptyDataError

from constants import DATA_PATH, HISTORIQUE_PATH, POSITIONS_PATH, DB_PATH
from services.storage import COLUMNS, HISTORIQUE_COLUMNS, POSITIONS_COLUMNS
from services import db

REFERENTIEL_PATH = "data/referentiel.csv"


def load_csv_or_empty(path: str, columns: list[str], **read_kw) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, **read_kw)
        if df.empty or list(df.columns) != columns:
            return pd.DataFrame(columns=columns)
        return df
    except (EmptyDataError, FileNotFoundError):
        return pd.DataFrame(columns=columns)


def main():
    print("Migration CSV -> SQLite")
    print("-" * 40)

    if not os.path.exists(DATA_PATH):
        print(f"  {DATA_PATH} introuvable. Création d'une base vide.")
    else:
        print(f"  Lecture de {DATA_PATH}")

    # 1. Créer la base et les tables
    db.init_db()
    print(f"  Base initialisée : {DB_PATH}")

    # 2. Actifs
    df_assets = load_csv_or_empty(DATA_PATH, COLUMNS)
    if "notes" in df_assets.columns:
        df_assets = df_assets.drop(columns=["notes"])
    # S'assurer que les colonnes attendues existent
    for col in COLUMNS:
        if col not in df_assets.columns:
            if col == "id":
                import uuid
                df_assets.insert(0, "id", [str(uuid.uuid4()) for _ in range(len(df_assets))])
            else:
                df_assets[col] = "" if col in ("nom", "categorie", "ticker", "courtier", "enveloppe") else 0.0

    if not df_assets.empty:
        db.save_assets(df_assets)
        print(f"  Actifs : {len(df_assets)} ligne(s)")
    else:
        print("  Actifs : 0 ligne (fichier vide ou absent)")

    # 3. Historique
    df_hist = load_csv_or_empty(HISTORIQUE_PATH, HISTORIQUE_COLUMNS, parse_dates=["date"])
    if not df_hist.empty:
        conn = db.get_conn()
        try:
            for _, row in df_hist.iterrows():
                d = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
                conn.execute(
                    "INSERT OR REPLACE INTO historique (asset_id, date, montant) VALUES (?, ?, ?)",
                    (str(row["asset_id"]), d, float(row["montant"])),
                )
            conn.commit()
            print(f"  Historique : {len(df_hist)} ligne(s)")
        finally:
            conn.close()
    else:
        print("  Historique : 0 ligne")

    # 4. Positions
    df_pos = load_csv_or_empty(POSITIONS_PATH, POSITIONS_COLUMNS, parse_dates=["date"])
    if not df_pos.empty:
        conn = db.get_conn()
        try:
            for _, row in df_pos.iterrows():
                d = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
                conn.execute(
                    "INSERT OR REPLACE INTO positions (asset_id, date, quantite) VALUES (?, ?, ?)",
                    (str(row["asset_id"]), d, float(row["quantite"])),
                )
            conn.commit()
            print(f"  Positions : {len(df_pos)} ligne(s)")
        finally:
            conn.close()
    else:
        print("  Positions : 0 ligne")

    # 5. Référentiel
    from constants import ENVELOPPES

    if os.path.exists(REFERENTIEL_PATH):
        try:
            df_ref = pd.read_csv(REFERENTIEL_PATH)
            if not df_ref.empty and "type" in df_ref.columns and "valeur" in df_ref.columns:
                conn = db.get_conn()
                try:
                    for _, row in df_ref.iterrows():
                        kind = str(row["type"]).strip().lower()
                        if kind not in ("courtier", "enveloppe"):
                            continue
                        conn.execute(
                            "INSERT OR IGNORE INTO referentiel (kind, value) VALUES (?, ?)",
                            (kind, str(row["valeur"]).strip()),
                        )
                    for env in ENVELOPPES:
                        conn.execute(
                            "INSERT OR IGNORE INTO referentiel (kind, value) VALUES ('enveloppe', ?)",
                            (env,),
                        )
                    conn.commit()
                    print(f"  Référentiel : {len(df_ref)} ligne(s) importées + enveloppes par défaut")
                finally:
                    conn.close()
            else:
                db.init_referentiel_from_assets(df_assets)
                print("  Référentiel : initialisé depuis les enveloppes par défaut")
        except Exception as e:
            db.init_referentiel_from_assets(df_assets)
            print(f"  Référentiel : erreur lecture CSV ({e}), initialisé par défaut")
    else:
        db.init_referentiel_from_assets(df_assets)
        print("  Référentiel : initialisé depuis actifs + enveloppes par défaut")

    print("-" * 40)
    print("Migration terminée. L'application utilise la base SQLite.")


if __name__ == "__main__":
    main()
