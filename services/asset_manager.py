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
    contrat_id: str = "",
) -> tuple[pd.DataFrame, str, str]:
    valid, err = validate_ticker(ticker)
    if not valid:
        return df, err, "error"

    nom = get_name(ticker)
    df = add_asset(df, nom, categorie, montant=0.0, ticker=ticker, quantite=quantite, pru=pru,
                   contrat_id=contrat_id)
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
    contrat_id: str = "",
    immo_params: dict | None = None,
) -> tuple[pd.DataFrame, str, str]:
    df = add_asset(df, nom, categorie, montant, contrat_id=contrat_id)
    if categorie == "Immobilier" and immo_params:
        last_idx = df.index[-1]
        for k, v in immo_params.items():
            df.loc[last_idx, k] = v
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
    contrat_id: str = "",
) -> tuple[pd.DataFrame, str, str]:
    valid, err = validate_ticker(ticker)
    if not valid:
        return df, err, "error"

    nom = get_name(ticker) if ticker != ticker_current else df.loc[idx, "nom"]
    montant = float(df.loc[idx, "montant"])

    df = update_asset(df, idx, nom, categorie, montant, ticker, quantite, pru,
                      contrat_id=contrat_id)
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
    contrat_id: str = "",
    immo_params: dict | None = None,
) -> tuple[pd.DataFrame, str, str]:
    montant_actuel = float(df.loc[idx, "montant"])

    df = update_asset(df, idx, nom, categorie, montant,
                      contrat_id=contrat_id)
    if categorie == "Immobilier" and immo_params:
        for k, v in immo_params.items():
            df.loc[idx, k] = v
    if montant != montant_actuel:
        record_montant(asset_id, montant)

    save_assets(df)

    return df, "Actif modifié", "success"


# ── Suppression ───────────────────────────────────────────────────────────────

def remove_asset(
    df: pd.DataFrame,
    idx: int,
    asset_id: str,
) -> tuple[pd.DataFrame, str, str]:
    delete_asset_history(asset_id)
    delete_asset_positions(asset_id)
    df = delete_asset(df, idx)
    save_assets(df)

    return df, "Actif supprimé", "success"


# ── Rafraîchissement des prix ─────────────────────────────────────────────────

def refresh_prices(df: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    df, errors = refresh_auto_assets(df, CATEGORIES_AUTO)
    save_assets(df)

    if errors:
        return df, f"Tickers introuvables : {', '.join(errors)}", "warning"
    return df, "Prix mis à jour", "success"


# ── Mise à jour datée ─────────────────────────────────────────────────────────

def update_at_date(
    df: pd.DataFrame,
    asset_id: str,
    categorie: str,
    op_date,
    quantite: float | None = None,
    pru: float | None = None,
    montant: float | None = None,
) -> tuple[pd.DataFrame, str, str]:
    """
    Enregistre l'état d'un actif à une date donnée.

    - Actif auto  : quantité totale + PRU à cette date
    - Actif manuel : montant total à cette date

    Permet de saisir une mise à jour rétroactive (ex : achat effectué
    le 15 mais saisi le 22 — on choisit le 15 comme date).
    Retourne (df_mis_à_jour, message, type_message).
    """
    idx_list = df.index[df["id"] == asset_id].tolist()
    if not idx_list:
        return df, "Actif introuvable.", "error"
    idx = idx_list[0]

    if categorie in CATEGORIES_AUTO:
        if quantite is None or pru is None:
            return df, "Quantité et PRU requis.", "error"

        record_position(asset_id, quantite, op_date)
        df.loc[idx, "quantite"] = quantite
        df.loc[idx, "pru"] = pru

        df, errors = refresh_auto_assets(df, CATEGORIES_AUTO)
        save_assets(df)

        if errors:
            return df, f"Mise à jour enregistrée, mais prix introuvable : {', '.join(errors)}", "warning"
        return df, "Mise à jour enregistrée", "success"

    else:
        if montant is None:
            return df, "Montant requis.", "error"

        record_montant(asset_id, montant, op_date)
        df.loc[idx, "montant"] = montant
        save_assets(df)
        return df, "Mise à jour enregistrée", "success"