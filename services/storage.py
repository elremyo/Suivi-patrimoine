import os
import pandas as pd
from pandas.errors import EmptyDataError

DATA_PATH = "data/patrimoine.csv"

COLUMNS = ["nom", "categorie", "montant", "ticker", "quantite", "pru"]


def init_storage():
    """Crée le fichier s'il n'existe pas."""
    if not os.path.exists(DATA_PATH):
        df = pd.DataFrame(columns=COLUMNS)
        df.to_csv(DATA_PATH, index=False)


def load_assets():
    try:
        df = pd.read_csv(DATA_PATH)
        if df.empty and list(df.columns) not in [COLUMNS]:
            df = pd.DataFrame(columns=COLUMNS)
        return df
    except (EmptyDataError, FileNotFoundError):
        df = pd.DataFrame(columns=COLUMNS)
        df.to_csv(DATA_PATH, index=False)
        return df


def save_assets(df):
    df.to_csv(DATA_PATH, index=False)


def download_assets(df):
    return df.to_csv(index=False).encode("utf-8")