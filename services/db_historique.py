"""
db_historique.py
───────────────
Gestion de l'historique des valeurs des actifs.
"""

import pandas as pd
from datetime import date
from .db import db_readonly, db_connection


def load_historique() -> pd.DataFrame:
    """Charge l'historique des montants par actif."""
    with db_readonly() as conn:
        df = pd.read_sql_query(
            "SELECT asset_id, date, montant FROM historique ORDER BY asset_id, date",
            conn,
        )
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
        return df


def record_montant(asset_id: str, montant: float, record_date: date | None = None) -> None:
    """
    Enregistre le montant d'un actif à une date donnée.
    Si un enregistrement existe déjà pour ce jour et cet actif, il est écrasé.
    """
    d = (record_date or date.today()).isoformat()
    with db_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO historique (asset_id, date, montant) VALUES (?, ?, ?)",
            (asset_id, d, float(montant)),
        )


def delete_asset_history(asset_id: str) -> None:
    """Supprime tout l'historique d'un actif (utile à la suppression d'un actif)."""
    with db_connection() as conn:
        conn.execute("DELETE FROM historique WHERE asset_id = ?", (asset_id,))
