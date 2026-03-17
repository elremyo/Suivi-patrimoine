"""
db_parametres.py
────────────────
Stockage de paramètres utilisateur (clé/valeur).
"""

from .db import db_readonly, db_connection


def get_parametre(cle: str, defaut=None):
    """Retourne la valeur d'un paramètre, ou defaut si absent."""
    with db_readonly() as conn:
        row = conn.execute(
            "SELECT valeur FROM parametres WHERE cle = ?", (cle,)
        ).fetchone()
        return row[0] if row else defaut


def set_parametre(cle: str, valeur) -> None:
    """Enregistre ou met à jour un paramètre."""
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO parametres (cle, valeur) VALUES (?, ?) "
            "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
            (cle, str(valeur)),
        )