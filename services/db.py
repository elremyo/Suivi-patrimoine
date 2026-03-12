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
    return sqlite3.connect(DB_PATH)


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
    # Ajout de contrat_id dans actifs si absent (base existante avant cette feature)
    cols = [row[1] for row in conn.execute("PRAGMA table_info(actifs)").fetchall()]
    if "contrat_id" not in cols:
        conn.execute("ALTER TABLE actifs ADD COLUMN contrat_id TEXT REFERENCES contrats(id) ON DELETE SET NULL")
        conn.commit()


