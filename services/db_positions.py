"""
db_positions.py
──────────────
Gestion des positions (quantités) des actifs à prix de marché.
"""

import pandas as pd
from datetime import date
from .db import get_conn


def load_positions() -> pd.DataFrame:
    """Charge l'historique des positions par actif."""
    df = pd.read_sql_query(
        "SELECT asset_id, date, quantite FROM positions ORDER BY asset_id, date",
        get_conn(),
    )
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def record_position(asset_id: str, quantite: float, record_date: date | None = None) -> None:
    """
    Enregistre la quantité détenue pour un actif à une date donnée.
    Si un enregistrement existe déjà pour ce jour, il est écrasé.
    """
    d = (record_date or date.today()).isoformat()
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO positions (asset_id, date, quantite) VALUES (?, ?, ?)",
            (asset_id, d, float(quantite)),
        )
        conn.commit()
    finally:
        conn.close()


def delete_asset_positions(asset_id: str) -> None:
    """Supprime toutes les positions d'un actif (utile à la suppression d'un actif)."""
    conn = get_conn()
    try:
        conn.execute("DELETE FROM positions WHERE asset_id = ?", (asset_id,))
        conn.commit()
    finally:
        conn.close()
