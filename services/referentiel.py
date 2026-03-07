"""
services/referentiel.py
────────────────────────
Gestion du référentiel courtiers et enveloppes.

Le référentiel est stocké dans data/referentiel.csv (ou table referentiel en SQLite).
    type  : "courtier" | "enveloppe"
    valeur: la valeur (ex. "Boursorama", "PEA")

Règles :
- Les enveloppes par défaut (ENVELOPPES dans constants.py) sont toujours
  présentes à l'initialisation.
- On peut supprimer un courtier ou une enveloppe seulement s'il n'est pas
  utilisé par un actif existant.
"""

import os
import pandas as pd
from pandas.errors import EmptyDataError
from constants import USE_SQLITE
from services.storage import safe_write_csv

REFERENTIEL_PATH = "data/referentiel.csv"
COLUMNS = ["type", "valeur"]


# ── Init & chargement ─────────────────────────────────────────────────────────

def init_referentiel(df_assets: pd.DataFrame | None = None):
    """
    Crée le fichier référentiel (ou table) s'il n'existe pas.
    Pré-remplit avec les enveloppes par défaut et les courtiers des actifs.
    """
    if USE_SQLITE:
        from services import db
        db.init_referentiel_from_assets(df_assets)
        return
    if os.path.exists(REFERENTIEL_PATH):
        return

    rows = []

    # Courtiers déjà utilisés dans les actifs existants
    if df_assets is not None and not df_assets.empty:
        for courtier in df_assets["courtier"].dropna().unique():
            courtier = str(courtier).strip()
            if courtier:
                rows.append({"type": "courtier", "valeur": courtier})

    df = pd.DataFrame(rows, columns=COLUMNS).drop_duplicates().reset_index(drop=True)
    safe_write_csv(df, REFERENTIEL_PATH)


def load_referentiel() -> pd.DataFrame:
    if USE_SQLITE:
        from services import db
        return db.load_referentiel()
    try:
        df = pd.read_csv(REFERENTIEL_PATH)
        if df.empty or list(df.columns) != COLUMNS:
            return pd.DataFrame(columns=COLUMNS)
        return df
    except (EmptyDataError, FileNotFoundError):
        return pd.DataFrame(columns=COLUMNS)


# ── Lecture ───────────────────────────────────────────────────────────────────

def get_courtiers() -> list[str]:
    df = load_referentiel()
    return sorted(df[df["type"] == "courtier"]["valeur"].tolist())



# ── Ajout ─────────────────────────────────────────────────────────────────────

def add_courtier(valeur: str) -> tuple[bool, str]:
    if USE_SQLITE:
        from services import db
        return db.add_courtier(valeur)
    valeur = valeur.strip()
    if not valeur:
        return False, "Le nom du courtier ne peut pas être vide."
    df = load_referentiel()
    exists = ((df["type"] == "courtier") & (df["valeur"] == valeur)).any()
    if exists:
        return False, f"« {valeur} » existe déjà."
    new_row = pd.DataFrame([{"type": "courtier", "valeur": valeur}])
    df = pd.concat([df, new_row], ignore_index=True)
    safe_write_csv(df, REFERENTIEL_PATH)
    return True, f"Courtier « {valeur} » ajouté."



# ── Suppression ───────────────────────────────────────────────────────────────

def delete_courtier(valeur: str, df_assets: pd.DataFrame) -> tuple[bool, str]:
    """Supprime un courtier seulement s'il n'est pas utilisé par un actif."""
    if USE_SQLITE:
        from services import db
        return db.delete_courtier(valeur, df_assets)
    if not df_assets.empty:
        used = (df_assets["courtier"].astype(str).str.strip() == valeur).any()
        if used:
            return False, f"« {valeur} » est encore utilisé par un actif — modifie l'actif d'abord."
    df = load_referentiel()
    df = df[~((df["type"] == "courtier") & (df["valeur"] == valeur))].reset_index(drop=True)
    safe_write_csv(df, REFERENTIEL_PATH)
    return True, f"Courtier « {valeur} » supprimé."



# ── Renommage ─────────────────────────────────────────────────────────────────

def rename_courtier(ancien: str, nouveau: str, df_assets: pd.DataFrame) -> tuple[bool, str, pd.DataFrame]:
    """
    Renomme un courtier dans le référentiel ET dans tous les actifs concernés.
    Retourne (succès, message, df_assets_mis_à_jour).
    """
    if USE_SQLITE:
        from services import db
        return db.rename_courtier(ancien, nouveau, df_assets)
    nouveau = nouveau.strip()
    if not nouveau:
        return False, "Le nouveau nom ne peut pas être vide.", df_assets
    if nouveau == ancien:
        return False, "Le nouveau nom est identique à l'ancien.", df_assets

    df_ref = load_referentiel()
    existe_deja = ((df_ref["type"] == "courtier") & (df_ref["valeur"] == nouveau)).any()
    if existe_deja:
        return False, f"« {nouveau} » existe déjà dans le référentiel.", df_assets

    # Mise à jour du référentiel
    df_ref.loc[(df_ref["type"] == "courtier") & (df_ref["valeur"] == ancien), "valeur"] = nouveau
    safe_write_csv(df_ref, REFERENTIEL_PATH)

    # Mise à jour des actifs concernés
    if not df_assets.empty:
        mask = df_assets["courtier"].astype(str).str.strip() == ancien
        df_assets = df_assets.copy()
        df_assets.loc[mask, "courtier"] = nouveau
        from constants import DATA_PATH
        safe_write_csv(df_assets, DATA_PATH)

    nb = int(mask.sum()) if not df_assets.empty else 0
    detail = f" ({nb} actif{'s' if nb > 1 else ''} mis à jour)" if nb > 0 else ""
    return True, f"Courtier renommé en « {nouveau} »{detail}.", df_assets