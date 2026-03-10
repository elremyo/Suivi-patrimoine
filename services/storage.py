import os
import pandas as pd

from services import db

COLUMNS = ["id", "nom", "categorie", "montant", "ticker", "quantite", "pru", "contrat_id"]


def init_storage():
    """Crée la base SQLite et les tables si nécessaire."""
    db.init_db()


def load_assets():
    return db.load_assets()


def save_assets(df):
    db.save_assets(df)


def reset_all_data() -> str:
    """Supprime la base locale pour repartir de zéro."""
    if os.path.exists(db.DB_PATH):
        os.remove(db.DB_PATH)
    return "Toutes les données ont été supprimées."


# ── Export ────────────────────────────────────────────────────────────────────

def download_assets(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def download_historique() -> bytes:
    """Retourne l'historique en CSV (bytes) pour téléchargement."""
    return db.download_historique_bytes()


def download_positions() -> bytes:
    """Retourne les positions en CSV (bytes) pour téléchargement."""
    return db.download_positions_bytes()
