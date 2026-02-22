import os
import pandas as pd
from pandas.errors import EmptyDataError

DATA_PATH = "data/patrimoine.csv"

COLUMNS = ["nom", "categorie", "montant"]


def init_storage():
    """Crée le fichier s'il n'existe pas."""
    if not os.path.exists(DATA_PATH):
        df = pd.DataFrame(columns=COLUMNS)
        df.to_csv(DATA_PATH, index=False)


def load_assets():
    try:
        df = pd.read_csv(DATA_PATH)
        if df.empty and list(df.columns) != COLUMNS:
            # fichier corrompu ou mal initialisé
            df = pd.DataFrame(columns=COLUMNS)
        return df
    except (EmptyDataError, FileNotFoundError):
        # fichier vide ou inexistant
        df = pd.DataFrame(columns=COLUMNS)
        df.to_csv(DATA_PATH, index=False)
        return df


def save_assets(df):
    df.to_csv(DATA_PATH, index=False)