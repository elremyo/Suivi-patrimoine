"""
db.py
─────
Utilitaires core de la base SQLite.
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from constants import DB_PATH


def _schema_path() -> str:
    return str(Path(__file__).resolve().parent.parent / "schema" / "schema.sql")


def get_conn() -> sqlite3.Connection:
    """Retourne une connexion à la base SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager pour les connexions SQLite.
    
    Gère automatiquement :
    - Ouverture de la connexion
    - Commit en cas de succès
    - Rollback en cas d'erreur
    - Fermeture systématique
    
    Usage:
        with db_connection() as conn:
            conn.execute("INSERT INTO actifs VALUES (?, ?)", (id, nom))
    """
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def db_readonly() -> Generator[sqlite3.Connection, None, None]:
    """Context manager pour les lectures seule (pas de commit/rollback).
    
    Usage:
        with db_readonly() as conn:
            df = pd.read_sql_query("SELECT * FROM actifs", conn)
    """
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Crée le fichier DB et les tables s'ils n'existent pas.
    Applique aussi les migrations nécessaires sur une base existante."""
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    schema_path = _schema_path()
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schéma introuvable : {schema_path}")
    with open(schema_path, encoding="utf-8") as f:
        sql = f.read()
    with db_connection() as conn:
        conn.executescript(sql)
        _migrate(conn)


def _migrate(conn: sqlite3.Connection) -> None:
    """Applique les migrations incrémentales sur une base existante."""
    # Migration 1 — contrat_id dans actifs
    cols = [row[1] for row in conn.execute("PRAGMA table_info(actifs)").fetchall()]
    if "contrat_id" not in cols:
        conn.execute("ALTER TABLE actifs ADD COLUMN contrat_id TEXT REFERENCES contrats(id) ON DELETE SET NULL")
        conn.commit()

    # Migration 2 — table parametres (clé/valeur)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS parametres (
            cle   TEXT PRIMARY KEY,
            valeur TEXT NOT NULL
        )
    """)
    conn.commit()

    # Migration 3 — nouveaux champs immobilier (coût réel + usage)
    immo_cols = [row[1] for row in conn.execute("PRAGMA table_info(actifs_immobilier)").fetchall()]
    if "frais_notaire" not in immo_cols:
        conn.execute("ALTER TABLE actifs_immobilier ADD COLUMN frais_notaire REAL DEFAULT 0")
        conn.execute("ALTER TABLE actifs_immobilier ADD COLUMN montant_travaux REAL DEFAULT 0")
        conn.execute("ALTER TABLE actifs_immobilier ADD COLUMN usage TEXT DEFAULT 'locatif'")
        conn.commit()

    # Migration 4 — suivi locatif
    immo_cols = [row[1] for row in conn.execute("PRAGMA table_info(actifs_immobilier)").fetchall()]
    if "loyer_mensuel" not in immo_cols:
        conn.execute("ALTER TABLE actifs_immobilier ADD COLUMN loyer_mensuel REAL DEFAULT 0")
        conn.execute("ALTER TABLE actifs_immobilier ADD COLUMN charges_mensuelles REAL DEFAULT 0")
        conn.execute("ALTER TABLE actifs_immobilier ADD COLUMN taxe_fonciere_annuelle REAL DEFAULT 0")
        conn.commit()

    # Migration 5 — suppression date_fin (redondante avec date_debut + duree_mois)
    emprunt_cols = [row[1] for row in conn.execute("PRAGMA table_info(emprunts)").fetchall()]
    if "date_fin" in emprunt_cols:
        conn.execute("ALTER TABLE emprunts DROP COLUMN date_fin")
        conn.commit()

    # Migration 6 — date_achat dans actifs_immobilier
    immo_cols = [row[1] for row in conn.execute("PRAGMA table_info(actifs_immobilier)").fetchall()]
    if "date_achat" not in immo_cols:
        conn.execute("ALTER TABLE actifs_immobilier ADD COLUMN date_achat TEXT")
        conn.commit()


def reset_all_data() -> str:
    """Supprime la base locale pour repartir de zéro."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    return "Toutes les données ont été supprimées."