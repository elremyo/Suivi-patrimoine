import os
import uuid
import pandas as pd
from filelock import FileLock
from pandas.errors import EmptyDataError
from constants import DATA_PATH, HISTORIQUE_PATH, POSITIONS_PATH, USE_SQLITE

COLUMNS = ["id", "nom", "categorie", "montant", "ticker", "quantite", "pru", "courtier", "enveloppe"]
HISTORIQUE_COLUMNS = ["asset_id", "date", "montant"]
POSITIONS_COLUMNS = ["asset_id", "date", "quantite"]


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
    """Crée le fichier (CSV ou DB) s'il n'existe pas."""
    if USE_SQLITE:
        from services import db
        db.init_db()
        return
    if not os.path.exists(DATA_PATH):
        df = pd.DataFrame(columns=COLUMNS)
        safe_write_csv(df, DATA_PATH)


def load_assets():
    if USE_SQLITE:
        from services import db
        return db.load_assets()
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
        # Migration : nouvelles colonnes courtier et enveloppe
        if "courtier" not in df.columns:
            df["courtier"] = ""
        if "enveloppe" not in df.columns:
            df["enveloppe"] = ""
        return df
    except (EmptyDataError, FileNotFoundError):
        df = pd.DataFrame(columns=COLUMNS)
        safe_write_csv(df, DATA_PATH)
        return df


def save_assets(df):
    if USE_SQLITE:
        from services import db
        db.save_assets(df)
        return
    safe_write_csv(df, DATA_PATH)


# ── Export ────────────────────────────────────────────────────────────────────

def download_assets(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def download_historique() -> bytes:
    """Lit et retourne le fichier historique en bytes pour téléchargement."""
    if USE_SQLITE:
        from services import db
        return db.download_historique_bytes()
    try:
        df = pd.read_csv(HISTORIQUE_PATH)
    except (EmptyDataError, FileNotFoundError):
        df = pd.DataFrame(columns=HISTORIQUE_COLUMNS)
    return df.to_csv(index=False).encode("utf-8")


def download_positions() -> bytes:
    """Lit et retourne le fichier positions en bytes pour téléchargement."""
    if USE_SQLITE:
        from services import db
        return db.download_positions_bytes()
    try:
        df = pd.read_csv(POSITIONS_PATH)
    except (EmptyDataError, FileNotFoundError):
        df = pd.DataFrame(columns=POSITIONS_COLUMNS)
    return df.to_csv(index=False).encode("utf-8")


# ── Import ────────────────────────────────────────────────────────────────────

def _validate_columns(df: pd.DataFrame, expected: list[str], label: str) -> tuple[bool, str]:
    """Vérifie que le DataFrame importé contient bien les colonnes attendues."""
    missing = [c for c in expected if c not in df.columns]
    if missing:
        return False, f"Fichier {label} invalide — colonnes manquantes : {', '.join(missing)}"
    return True, ""


def import_assets(uploaded_file) -> tuple[bool, str]:
    """
    Remplace le fichier actifs par le CSV uploadé.
    Retourne (succès, message).
    """
    try:
        df = pd.read_csv(uploaded_file)
        ok, err = _validate_columns(df, ["nom", "categorie", "montant"], "actifs")
        if not ok:
            return False, err
        # Colonnes optionnelles : on les ajoute si absentes (compatibilité)
        if "id" not in df.columns:
            df.insert(0, "id", [str(uuid.uuid4()) for _ in range(len(df))])
        for col, default in [("ticker", ""), ("quantite", 0.0), ("pru", 0.0),
                              ("courtier", ""), ("enveloppe", "")]:
            if col not in df.columns:
                df[col] = default
        if USE_SQLITE:
            from services import db
            db.save_assets(df)
        else:
            safe_write_csv(df, DATA_PATH)
        return True, f"{len(df)} actif(s) importé(s) avec succès."
    except Exception as e:
        return False, f"Erreur lors de l'import des actifs : {e}"


def import_historique(uploaded_file) -> tuple[bool, str]:
    """
    Remplace le fichier historique par le CSV uploadé.
    Retourne (succès, message).
    """
    try:
        df = pd.read_csv(uploaded_file, parse_dates=["date"])
        ok, err = _validate_columns(df, HISTORIQUE_COLUMNS, "historique")
        if not ok:
            return False, err
        if USE_SQLITE:
            from services import db
            conn = db.get_conn()
            try:
                conn.execute("DELETE FROM historique")
                for _, row in df.iterrows():
                    d = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
                    conn.execute(
                        "INSERT INTO historique (asset_id, date, montant) VALUES (?, ?, ?)",
                        (str(row["asset_id"]), d, float(row["montant"])),
                    )
                conn.commit()
            finally:
                conn.close()
        else:
            safe_write_csv(df, HISTORIQUE_PATH)
        return True, f"{len(df)} entrée(s) d'historique importée(s) avec succès."
    except Exception as e:
        return False, f"Erreur lors de l'import de l'historique : {e}"


def import_positions(uploaded_file) -> tuple[bool, str]:
    """
    Remplace le fichier positions par le CSV uploadé.
    Retourne (succès, message).
    """
    try:
        df = pd.read_csv(uploaded_file, parse_dates=["date"])
        ok, err = _validate_columns(df, POSITIONS_COLUMNS, "positions")
        if not ok:
            return False, err
        if USE_SQLITE:
            from services import db
            conn = db.get_conn()
            try:
                conn.execute("DELETE FROM positions")
                for _, row in df.iterrows():
                    d = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
                    conn.execute(
                        "INSERT INTO positions (asset_id, date, quantite) VALUES (?, ?, ?)",
                        (str(row["asset_id"]), d, float(row["quantite"])),
                    )
                conn.commit()
            finally:
                conn.close()
        else:
            safe_write_csv(df, POSITIONS_PATH)
        return True, f"{len(df)} position(s) importée(s) avec succès."
    except Exception as e:
        return False, f"Erreur lors de l'import des positions : {e}"