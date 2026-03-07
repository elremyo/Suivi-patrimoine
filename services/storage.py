import uuid
import pandas as pd

from services import db

COLUMNS = ["id", "nom", "categorie", "montant", "ticker", "quantite", "pru", "courtier", "enveloppe"]
HISTORIQUE_COLUMNS = ["asset_id", "date", "montant"]
POSITIONS_COLUMNS = ["asset_id", "date", "quantite"]


def init_storage():
    """Crée la base SQLite et les tables si nécessaire."""
    db.init_db()


def load_assets():
    return db.load_assets()


def save_assets(df):
    db.save_assets(df)


# ── Export ────────────────────────────────────────────────────────────────────

def download_assets(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def download_historique() -> bytes:
    """Retourne l'historique en CSV (bytes) pour téléchargement."""
    return db.download_historique_bytes()


def download_positions() -> bytes:
    """Retourne les positions en CSV (bytes) pour téléchargement."""
    return db.download_positions_bytes()


# ── Import ────────────────────────────────────────────────────────────────────

def _validate_columns(df: pd.DataFrame, expected: list[str], label: str) -> tuple[bool, str]:
    """Vérifie que le DataFrame importé contient bien les colonnes attendues."""
    missing = [c for c in expected if c not in df.columns]
    if missing:
        return False, f"Fichier {label} invalide — colonnes manquantes : {', '.join(missing)}"
    return True, ""


def import_assets(uploaded_file) -> tuple[bool, str]:
    """
    Remplace les actifs par le contenu du CSV uploadé.
    Retourne (succès, message).
    """
    try:
        df = pd.read_csv(uploaded_file)
        ok, err = _validate_columns(df, ["nom", "categorie", "montant"], "actifs")
        if not ok:
            return False, err
        if "id" not in df.columns:
            df.insert(0, "id", [str(uuid.uuid4()) for _ in range(len(df))])
        for col, default in [("ticker", ""), ("quantite", 0.0), ("pru", 0.0),
                              ("courtier", ""), ("enveloppe", "")]:
            if col not in df.columns:
                df[col] = default
        db.save_assets(df)
        return True, f"{len(df)} actif(s) importé(s) avec succès."
    except Exception as e:
        return False, f"Erreur lors de l'import des actifs : {e}"


def import_historique(uploaded_file) -> tuple[bool, str]:
    """
    Remplace l'historique par le CSV uploadé.
    Retourne (succès, message).
    """
    try:
        df = pd.read_csv(uploaded_file, parse_dates=["date"])
        ok, err = _validate_columns(df, HISTORIQUE_COLUMNS, "historique")
        if not ok:
            return False, err
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
        return True, f"{len(df)} entrée(s) d'historique importée(s) avec succès."
    except Exception as e:
        return False, f"Erreur lors de l'import de l'historique : {e}"


def import_positions(uploaded_file) -> tuple[bool, str]:
    """
    Remplace les positions par le CSV uploadé.
    Retourne (succès, message).
    """
    try:
        df = pd.read_csv(uploaded_file, parse_dates=["date"])
        ok, err = _validate_columns(df, POSITIONS_COLUMNS, "positions")
        if not ok:
            return False, err
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
        return True, f"{len(df)} position(s) importée(s) avec succès."
    except Exception as e:
        return False, f"Erreur lors de l'import des positions : {e}"
