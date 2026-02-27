import os
import uuid
import pandas as pd
from filelock import FileLock
from pandas.errors import EmptyDataError
from constants import DATA_PATH

COLUMNS = ["id", "nom", "categorie", "montant", "ticker", "quantite", "pru"]


def _lock_path(csv_path: str) -> str:
    """Retourne le chemin du fichier de verrou associé à un CSV."""
    return csv_path + ".lock"


def safe_write_csv(df: pd.DataFrame, path: str) -> None:
    """
    Écrit un DataFrame en CSV de manière sécurisée :
    - Pose un verrou exclusif sur le fichier pendant l'écriture
    - Empêche les écritures simultanées depuis plusieurs onglets/sessions
    - Le verrou est automatiquement relâché après l'écriture (même en cas d'erreur)

    À utiliser à la place de df.to_csv() partout dans le projet.
    """
    lock = FileLock(_lock_path(path), timeout=5)
    with lock:
        df.to_csv(path, index=False)


def init_storage():
    """Crée le fichier s'il n'existe pas."""
    if not os.path.exists(DATA_PATH):
        df = pd.DataFrame(columns=COLUMNS)
        safe_write_csv(df, DATA_PATH)


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
        safe_write_csv(df, DATA_PATH)
        return df


def save_assets(df):
    safe_write_csv(df, DATA_PATH)


def download_assets(df):
    return df.to_csv(index=False).encode("utf-8")