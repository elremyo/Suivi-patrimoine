"""
services/referentiel.py
────────────────────────
Gestion du référentiel courtiers et enveloppes (stockage SQLite).
    type  : "courtier" | "enveloppe"
    valeur: la valeur (ex. "Boursorama", "PEA")

Règles :
- Les enveloppes par défaut (ENVELOPPES dans constants.py) sont toujours
  présentes à l'initialisation.
- On peut supprimer un courtier seulement s'il n'est pas utilisé par un actif.
"""

import pandas as pd

from services import db


def init_referentiel(df_assets: pd.DataFrame | None = None):
    """
    Pré-remplit le référentiel (table SQLite) avec les enveloppes par défaut
    et les courtiers déjà présents dans les actifs, si la table est vide.
    """
    db.init_referentiel_from_assets(df_assets)


def load_referentiel() -> pd.DataFrame:
    return db.load_referentiel()


def get_courtiers() -> list[str]:
    df = load_referentiel()
    return sorted(df[df["type"] == "courtier"]["valeur"].tolist())


def add_courtier(valeur: str) -> tuple[bool, str]:
    return db.add_courtier(valeur)


def delete_courtier(valeur: str, df_assets: pd.DataFrame) -> tuple[bool, str]:
    """Supprime un courtier seulement s'il n'est pas utilisé par un actif."""
    return db.delete_courtier(valeur, df_assets)


def rename_courtier(ancien: str, nouveau: str, df_assets: pd.DataFrame) -> tuple[bool, str, pd.DataFrame]:
    """
    Renomme un courtier dans le référentiel ET dans tous les actifs concernés.
    Retourne (succès, message, df_assets_mis_à_jour).
    """
    return db.rename_courtier(ancien, nouveau, df_assets)
