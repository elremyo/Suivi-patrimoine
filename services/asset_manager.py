"""
asset_manager.py
────────────────
Séquences métier complètes sur les actifs.
Chaque fonction coordonne plusieurs services (assets, historique, positions, pricer)
et retourne un tuple (df_mis_à_jour, message, type_message).

L'UI (app.py) ne fait qu'appeler ces fonctions et afficher le résultat —
elle ne contient plus aucune logique métier.

Types de message : "success" | "warning" | "error"
"""

import pandas as pd
from services.assets import add_asset, update_asset, delete_asset
from services.historique import record_montant, delete_asset_history
from services.positions import record_position, delete_asset_positions
from services.pricer import get_name, refresh_auto_assets, validate_ticker
from services.storage import save_assets
from constants import CATEGORIES_AUTO


# ── Création ──────────────────────────────────────────────────────────────────

def create_auto_asset(
    df: pd.DataFrame,
    ticker: str,
    quantite: float,
    pru: float,
    categorie: str,
) -> tuple[pd.DataFrame, str, str]:
    """
    Crée un actif automatique (Actions & Fonds, Crypto) :
    1. Valide le format du ticker
    2. Récupère le nom depuis yfinance
    3. Ajoute l'actif au DataFrame
    4. Enregistre la position initiale
    5. Rafraîchit le prix
    6. Sauvegarde sur le disque
    """
    valid, err = validate_ticker(ticker)
    if not valid:
        return df, err, "error"

    nom = get_name(ticker)
    df = add_asset(df, nom, categorie, montant=0.0, ticker=ticker, quantite=quantite, pru=pru)
    asset_id = df.iloc[-1]["id"]
    record_position(asset_id, quantite)
    df, errors = refresh_auto_assets(df, CATEGORIES_AUTO)
    save_assets(df)

    if errors:
        return df, f"Actif ajouté ({nom}), mais ticker introuvable : {', '.join(errors)}", "warning"
    return df, f"Actif ajouté et prix synchronisé ({nom})", "success"


def create_manual_asset(
    df: pd.DataFrame,
    nom: str,
    categorie: str,
    montant: float,
) -> tuple[pd.DataFrame, str, str]:
    """
    Crée un actif manuel (Livrets, Immobilier, Fonds euros) :
    1. Ajoute l'actif au DataFrame
    2. Enregistre le montant dans l'historique
    3. Sauvegarde sur le disque
    """
    df = add_asset(df, nom, categorie, montant)
    asset_id = df.iloc[-1]["id"]
    record_montant(asset_id, montant)
    save_assets(df)

    return df, "Actif ajouté", "success"


# ── Modification ──────────────────────────────────────────────────────────────

def edit_auto_asset(
    df: pd.DataFrame,
    idx: int,
    asset_id: str,
    ticker: str,
    ticker_current: str,
    quantite: float,
    quantite_current: float,
    pru: float,
    categorie: str,
) -> tuple[pd.DataFrame, str, str]:
    """
    Modifie un actif automatique :
    1. Valide le format du ticker
    2. Récupère le nouveau nom si le ticker a changé
    3. Met à jour l'actif
    4. Enregistre une nouvelle position si la quantité a changé
    5. Rafraîchit le prix
    6. Sauvegarde sur le disque
    """
    valid, err = validate_ticker(ticker)
    if not valid:
        return df, err, "error"

    nom = get_name(ticker) if ticker != ticker_current else df.loc[idx, "nom"]
    montant = float(df.loc[idx, "montant"])

    df = update_asset(df, idx, nom, categorie, montant, ticker, quantite, pru)
    if quantite != quantite_current:
        record_position(asset_id, quantite)
    df, errors = refresh_auto_assets(df, CATEGORIES_AUTO)
    save_assets(df)

    if errors:
        return df, f"Actif modifié, mais ticker introuvable : {', '.join(errors)}", "warning"
    return df, "Actif modifié et prix synchronisé", "success"


def edit_manual_asset(
    df: pd.DataFrame,
    idx: int,
    asset_id: str,
    nom: str,
    categorie: str,
    montant: float,
) -> tuple[pd.DataFrame, str, str]:
    """
    Modifie un actif manuel :
    1. Met à jour l'actif
    2. Enregistre le nouveau montant dans l'historique
    3. Sauvegarde sur le disque
    """
    df = update_asset(df, idx, nom, categorie, montant)
    record_montant(asset_id, montant)
    save_assets(df)

    return df, "Actif modifié", "success"


# ── Suppression ───────────────────────────────────────────────────────────────

def remove_asset(
    df: pd.DataFrame,
    idx: int,
    asset_id: str,
) -> tuple[pd.DataFrame, str, str]:
    """
    Supprime un actif et toutes ses données associées :
    1. Supprime l'historique des montants
    2. Supprime l'historique des positions
    3. Supprime l'actif du DataFrame
    4. Sauvegarde sur le disque
    """
    delete_asset_history(asset_id)
    delete_asset_positions(asset_id)
    df = delete_asset(df, idx)
    save_assets(df)

    return df, "Actif supprimé", "success"


# ── Rafraîchissement des prix ─────────────────────────────────────────────────

def refresh_prices(df: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    """
    Rafraîchit les prix de tous les actifs automatiques :
    1. Récupère les derniers prix depuis yfinance
    2. Met à jour les montants
    3. Sauvegarde sur le disque
    """
    df, errors = refresh_auto_assets(df, CATEGORIES_AUTO)
    save_assets(df)

    if errors:
        return df, f"Tickers introuvables : {', '.join(errors)}", "warning"
    return df, "Prix mis à jour", "success"