"""
services/referentiel.py
────────────────────────
Gestion du référentiel courtiers et enveloppes.

Le référentiel est stocké dans data/referentiel.csv avec deux colonnes :
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
from services.storage import safe_write_csv
from constants import ENVELOPPES

REFERENTIEL_PATH = "data/referentiel.csv"
COLUMNS = ["type", "valeur"]


# ── Init & chargement ─────────────────────────────────────────────────────────

def init_referentiel(df_assets: pd.DataFrame | None = None):
    """
    Crée le fichier référentiel s'il n'existe pas.
    Pré-remplit avec :
      - les enveloppes par défaut de constants.py
      - les courtiers et enveloppes déjà présents dans les actifs existants
    """
    if os.path.exists(REFERENTIEL_PATH):
        return

    rows = []

    # Enveloppes par défaut
    for env in ENVELOPPES:
        rows.append({"type": "enveloppe", "valeur": env})

    # Valeurs déjà utilisées dans les actifs existants
    if df_assets is not None and not df_assets.empty:
        for courtier in df_assets["courtier"].dropna().unique():
            courtier = str(courtier).strip()
            if courtier:
                rows.append({"type": "courtier", "valeur": courtier})

        for env in df_assets["enveloppe"].dropna().unique():
            env = str(env).strip()
            if env and not any(r["type"] == "enveloppe" and r["valeur"] == env for r in rows):
                rows.append({"type": "enveloppe", "valeur": env})

    df = pd.DataFrame(rows, columns=COLUMNS).drop_duplicates().reset_index(drop=True)
    safe_write_csv(df, REFERENTIEL_PATH)


def load_referentiel() -> pd.DataFrame:
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


def get_enveloppes() -> list[str]:
    df = load_referentiel()
    return sorted(df[df["type"] == "enveloppe"]["valeur"].tolist())


# ── Ajout ─────────────────────────────────────────────────────────────────────

def add_courtier(valeur: str) -> tuple[bool, str]:
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


def add_enveloppe(valeur: str) -> tuple[bool, str]:
    valeur = valeur.strip()
    if not valeur:
        return False, "Le nom de l'enveloppe ne peut pas être vide."
    df = load_referentiel()
    exists = ((df["type"] == "enveloppe") & (df["valeur"] == valeur)).any()
    if exists:
        return False, f"« {valeur} » existe déjà."
    new_row = pd.DataFrame([{"type": "enveloppe", "valeur": valeur}])
    df = pd.concat([df, new_row], ignore_index=True)
    safe_write_csv(df, REFERENTIEL_PATH)
    return True, f"Enveloppe « {valeur} » ajoutée."


# ── Suppression ───────────────────────────────────────────────────────────────

def delete_courtier(valeur: str, df_assets: pd.DataFrame) -> tuple[bool, str]:
    """Supprime un courtier seulement s'il n'est pas utilisé par un actif."""
    if not df_assets.empty:
        used = (df_assets["courtier"].astype(str).str.strip() == valeur).any()
        if used:
            return False, f"« {valeur} » est encore utilisé par un actif — modifie l'actif d'abord."
    df = load_referentiel()
    df = df[~((df["type"] == "courtier") & (df["valeur"] == valeur))].reset_index(drop=True)
    safe_write_csv(df, REFERENTIEL_PATH)
    return True, f"Courtier « {valeur} » supprimé."


def delete_enveloppe(valeur: str, df_assets: pd.DataFrame) -> tuple[bool, str]:
    """Supprime une enveloppe seulement si elle n'est pas utilisée par un actif."""
    if not df_assets.empty:
        used = (df_assets["enveloppe"].astype(str).str.strip() == valeur).any()
        if used:
            return False, f"« {valeur} » est encore utilisée par un actif — modifie l'actif d'abord."
    df = load_referentiel()
    df = df[~((df["type"] == "enveloppe") & (df["valeur"] == valeur))].reset_index(drop=True)
    safe_write_csv(df, REFERENTIEL_PATH)
    return True, f"Enveloppe « {valeur} » supprimée."


# ── Renommage ─────────────────────────────────────────────────────────────────

def rename_courtier(ancien: str, nouveau: str, df_assets: pd.DataFrame) -> tuple[bool, str, pd.DataFrame]:
    """
    Renomme un courtier dans le référentiel ET dans tous les actifs concernés.
    Retourne (succès, message, df_assets_mis_à_jour).
    """
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
        df_assets.loc[mask, "courtier"] = nouveau
        from constants import DATA_PATH
        safe_write_csv(df_assets, DATA_PATH)

    nb = int(mask.sum()) if not df_assets.empty else 0
    detail = f" ({nb} actif{'s' if nb > 1 else ''} mis à jour)" if nb > 0 else ""
    return True, f"Courtier renommé en « {nouveau} »{detail}.", df_assets