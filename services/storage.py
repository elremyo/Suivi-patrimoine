import os
import uuid
import pandas as pd
from pandas.errors import EmptyDataError

DATA_PATH = "data/patrimoine.csv"

COLUMNS = ["id", "nom", "categorie", "montant", "ticker", "quantite", "pru"]


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
        # Migration : anciens fichiers sans les nouvelles colonnes
        if "notes" in df.columns:
            df = df.drop(columns=["notes"])
        if "id" not in df.columns:
            df.insert(0, "id", [str(uuid.uuid4()) for _ in range(len(df))])
        if "ticker" not in df.columns:
            df["ticker"] = ""
        if "quantite" not in df.columns:
            df["quantite"] = 0.0
        if "pru" not in df.columns:
            df["pru"] = 0.0
        return df
    except (EmptyDataError, FileNotFoundError):
        df = pd.DataFrame(columns=COLUMNS)
        df.to_csv(DATA_PATH, index=False)
        return df


def save_assets(df):
    df.to_csv(DATA_PATH, index=False)


def download_assets(df):
    return df.to_csv(index=False).encode("utf-8")