import pandas as pd
import streamlit as st
from datetime import date

from constants import CACHE_TTL_SECONDS
from services import db


def init_historique():
    """Les tables sont créées par init_storage (db.init_db())."""
    pass


def load_historique() -> pd.DataFrame:
    return db.load_historique()


def record_montant(asset_id: str, montant: float, record_date: date | None = None):
    """
    Enregistre le montant d'un actif manuel à une date donnée.
    Si un enregistrement existe déjà pour ce jour et cet actif, il est écrasé.
    """
    db.record_montant(asset_id, montant, record_date)


def delete_asset_history(asset_id: str):
    """Supprime tout l'historique d'un actif (utile à la suppression d'un actif)."""
    db.delete_asset_history(asset_id)


def get_montant_at(asset_id: str, at_date: pd.Timestamp, df_hist: pd.DataFrame) -> float | None:
    """
    Retourne le dernier montant connu pour un actif manuel avant ou à at_date.
    Retourne None si aucun enregistrement n'existe.
    """
    asset_hist = df_hist[df_hist["asset_id"] == asset_id]
    past = asset_hist[asset_hist["date"] <= at_date]
    if past.empty:
        return None
    return float(past.sort_values("date").iloc[-1]["montant"])


# ── Fonctions publiques d'évolution ──────────────────────────────────────────

@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def build_total_evolution(
    df_assets: pd.DataFrame,
    df_hist: pd.DataFrame,
    df_positions: pd.DataFrame,
    df_prices: pd.DataFrame,
    categories_auto: tuple,  # tuple pour être hashable par st.cache_data
) -> pd.DataFrame:
    """
    Retourne un DataFrame { date, total } avec la valeur totale du patrimoine
    pour chaque date disponible dans l'historique.
    """
    raw = _compute_raw_evolution(df_assets, df_hist, df_positions, df_prices, categories_auto)
    if raw.empty:
        return pd.DataFrame(columns=["date", "total"])

    result = raw.groupby("date")["valeur"].sum().reset_index()
    result.columns = ["date", "total"]
    return result.sort_values("date").reset_index(drop=True)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def build_category_evolution(
    df_assets: pd.DataFrame,
    df_hist: pd.DataFrame,
    df_positions: pd.DataFrame,
    df_prices: pd.DataFrame,
    categories_auto: tuple,
) -> pd.DataFrame:
    """
    Retourne un DataFrame pivot date × catégorie avec la valeur de chaque catégorie
    pour chaque date disponible dans l'historique.
    """
    raw = _compute_raw_evolution(df_assets, df_hist, df_positions, df_prices, categories_auto)
    if raw.empty:
        return pd.DataFrame()

    pivot = raw.groupby(["date", "categorie"])["valeur"].sum().unstack(fill_value=0)
    pivot.index = pd.to_datetime(pivot.index)
    return pivot.sort_index()


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def build_asset_evolution(
    df_assets: pd.DataFrame,
    df_hist: pd.DataFrame,
    df_positions: pd.DataFrame,
    df_prices: pd.DataFrame,
    categories_auto: tuple,
) -> pd.DataFrame:
    """
    Retourne un DataFrame pivot date × nom d'actif avec la valeur de chaque actif
    pour chaque date disponible dans l'historique.
    """
    raw = _compute_raw_evolution(df_assets, df_hist, df_positions, df_prices, categories_auto)
    if raw.empty:
        return pd.DataFrame()

    pivot = raw.groupby(["date", "nom"])["valeur"].sum().unstack(fill_value=0)
    pivot.index = pd.to_datetime(pivot.index)
    return pivot.sort_index()


def _compute_raw_evolution(
    df_assets: pd.DataFrame,
    df_hist: pd.DataFrame,
    df_positions: pd.DataFrame,
    df_prices: pd.DataFrame,
    categories_auto: tuple,
) -> pd.DataFrame:
    """
    Calcule la valeur de chaque actif à chaque date disponible.
    Retourne un DataFrame à format long : date | asset_id | nom | categorie | valeur
    """
    if df_assets.empty:
        return pd.DataFrame()

    all_dates = _collect_all_dates(df_hist, df_prices)
    if all_dates.empty:
        return pd.DataFrame()

    earliest = _earliest_known_date(df_hist, df_positions)
    if earliest is not None:
        all_dates = all_dates[all_dates >= earliest]

    dates_df = pd.DataFrame({"date": all_dates})
    parts = []

    auto_mask = df_assets["categorie"].isin(categories_auto) & (df_assets["ticker"] != "")
    manual_assets = df_assets[~auto_mask]
    auto_assets = df_assets[auto_mask]

    if not manual_assets.empty and not df_hist.empty:
        hist_sorted = df_hist.sort_values("date")
        for _, asset in manual_assets.iterrows():
            asset_hist = hist_sorted[hist_sorted["asset_id"] == asset["id"]]
            if asset_hist.empty:
                continue
            merged = pd.merge_asof(
                dates_df,
                asset_hist[["date", "montant"]],
                on="date",
                direction="backward",
            )
            merged = merged.dropna(subset=["montant"])
            if merged.empty:
                continue
            merged["asset_id"] = asset["id"]
            merged["nom"] = asset["nom"]
            merged["categorie"] = asset["categorie"]
            merged = merged.rename(columns={"montant": "valeur"})
            parts.append(merged[["date", "asset_id", "nom", "categorie", "valeur"]])

    if not auto_assets.empty and not df_prices.empty and not df_positions.empty:
        prices_long = df_prices.stack().reset_index()
        prices_long.columns = ["date", "ticker", "price"]
        prices_long["date"] = pd.to_datetime(prices_long["date"]).dt.normalize()
        prices_long = prices_long.sort_values("date")
        positions_sorted = df_positions.sort_values("date")

        for _, asset in auto_assets.iterrows():
            ticker = asset["ticker"]
            if ticker not in df_prices.columns:
                continue
            asset_prices = prices_long[prices_long["ticker"] == ticker]
            asset_positions = positions_sorted[positions_sorted["asset_id"] == asset["id"]]
            if asset_positions.empty:
                continue
            merged = pd.merge_asof(
                dates_df,
                asset_prices[["date", "price"]],
                on="date",
                direction="backward",
            )
            merged = pd.merge_asof(
                merged,
                asset_positions[["date", "quantite"]],
                on="date",
                direction="backward",
            )
            merged = merged.dropna(subset=["quantite", "price"])
            if merged.empty:
                continue
            merged["valeur"] = (merged["price"] * merged["quantite"]).round(2)
            merged["asset_id"] = asset["id"]
            merged["nom"] = asset["nom"]
            merged["categorie"] = asset["categorie"]
            parts.append(merged[["date", "asset_id", "nom", "categorie", "valeur"]])

    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def _collect_all_dates(df_hist: pd.DataFrame, df_prices: pd.DataFrame) -> pd.DatetimeIndex:
    """Collecte toutes les dates disponibles dans les deux sources."""
    dates = set()
    if not df_hist.empty:
        dates.update(df_hist["date"].dt.normalize().unique())
    if not df_prices.empty:
        dates.update(pd.to_datetime(df_prices.index).normalize())
    if not dates:
        return pd.DatetimeIndex([])
    return pd.DatetimeIndex(sorted(dates))


def _earliest_known_date(df_hist: pd.DataFrame, df_positions: pd.DataFrame) -> pd.Timestamp | None:
    """Retourne la plus ancienne date où on a une donnée (historique manuel ou position)."""
    candidates = []
    if not df_hist.empty:
        candidates.append(df_hist["date"].min())
    if not df_positions.empty:
        candidates.append(df_positions["date"].min())
    if not candidates:
        return None
    return min(candidates)