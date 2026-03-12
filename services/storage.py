import os
import pandas as pd

from services import db

COLUMNS = ["id", "nom", "categorie", "montant", "ticker", "quantite", "pru", "contrat_id"]


def init_storage():
    """Crée la base SQLite et les tables si nécessaire."""
    db.init_db()


def load_assets():
    from services.db_actifs import load_assets
    return load_assets()


def save_assets(df):
    from services.db_actifs import save_assets
    save_assets(df)


def reset_all_data() -> str:
    """Supprime la base locale pour repartir de zéro."""
    if os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)
    return "Toutes les données ont été supprimées."
