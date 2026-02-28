import os
import pandas as pd
from datetime import date
from pandas.errors import EmptyDataError
from constants import HISTORIQUE_PATH
from services.storage import safe_write_csv


COLUMNS = ["asset_id", "date", "montant"]


def init_historique():
    if not os.path.exists(HISTORIQUE_PATH):
        safe_write_csv(pd.DataFrame(columns=COLUMNS), HISTORIQUE_PATH)


def load_historique() -> pd.DataFrame:
    try:
        df = pd.read_csv(HISTORIQUE_PATH, parse_dates=["date"])
        if df.empty or list(df.columns) != COLUMNS:
            return pd.DataFrame(columns=COLUMNS)
        return df
    except (EmptyDataError, FileNotFoundError):
        return pd.DataFrame(columns=COLUMNS)


def record_montant(asset_id: str, montant: float, record_date: date | None = None):
    """
    Enregistre le montant d'un actif manuel à une date donnée.
    Si un enregistrement existe déjà pour ce jour et cet actif, il est écrasé.
    """
    d = pd.Timestamp(record_date or date.today())
    df = load_historique()

    if not df.empty:
        df = df[~((df["asset_id"] == asset_id) & (df["date"] == d))]

    new_row = pd.DataFrame([[asset_id, d, montant]], columns=COLUMNS)
    if df.empty:
        df = new_row.reset_index(drop=True)
    else:
        df = pd.concat([df, new_row], ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["asset_id", "date"]).reset_index(drop=True)
    safe_write_csv(df, HISTORIQUE_PATH)


def delete_asset_history(asset_id: str):
    """Supprime tout l'historique d'un actif (utile à la suppression d'un actif)."""
    df = load_historique()
    if df.empty:
        return
    df = df[df["asset_id"] != asset_id].reset_index(drop=True)
    safe_write_csv(df, HISTORIQUE_PATH)


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

def build_total_evolution(
    df_assets: pd.DataFrame,
    df_hist: pd.DataFrame,
    df_positions: pd.DataFrame,
    df_prices: pd.DataFrame,
    categories_auto: set,
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


def build_category_evolution(
    df_assets: pd.DataFrame,
    df_hist: pd.DataFrame,
    df_positions: pd.DataFrame,
    df_prices: pd.DataFrame,
    categories_auto: set,
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


def build_asset_evolution(
    df_assets: pd.DataFrame,
    df_hist: pd.DataFrame,
    df_positions: pd.DataFrame,
    df_prices: pd.DataFrame,
    categories_auto: set,
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


# ── Cœur du calcul — fonction privée ─────────────────────────────────────────

def _compute_raw_evolution(
    df_assets: pd.DataFrame,
    df_hist: pd.DataFrame,
    df_positions: pd.DataFrame,
    df_prices: pd.DataFrame,
    categories_auto: set,
) -> pd.DataFrame:
    """
    Calcule la valeur de chaque actif à chaque date disponible.

    Retourne un DataFrame à format long :
        date | asset_id | nom | categorie | valeur

    C'est la source unique utilisée par build_total_evolution,
    build_category_evolution et build_asset_evolution.

    Approche vectorisée : on boucle sur les actifs (ex. 10),
    pas sur dates × actifs (ex. 3 650). Pour chaque actif,
    merge_asof résout toutes les dates en une seule opération pandas.
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

    # ── Actifs manuels ────────────────────────────────────────────────────────
    # Pour chaque actif manuel : merge_asof entre toutes les dates et son historique.
    # Cela retourne, pour chaque date, le dernier montant connu avant cette date.
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
            merged["asset_id"]  = asset["id"]
            merged["nom"]       = asset["nom"]
            merged["categorie"] = asset["categorie"]
            merged = merged.rename(columns={"montant": "valeur"})
            parts.append(merged[["date", "asset_id", "nom", "categorie", "valeur"]])

    # ── Actifs automatiques ───────────────────────────────────────────────────
    # On convertit df_prices en format long (date, ticker, price) une seule fois,
    # puis pour chaque actif auto on fait deux merge_asof :
    #   1. prix historique à chaque date
    #   2. quantité détenue à chaque date
    # La valeur est ensuite prix × quantité.
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

            # Pour chaque date de prix, trouver la dernière quantité connue
            merged = pd.merge_asof(
                asset_prices,
                asset_positions[["date", "quantite"]],
                on="date",
                direction="backward",
            )
            merged = merged.dropna(subset=["quantite"])
            # Garder uniquement les dates qui sont dans all_dates
            merged = merged[merged["date"].isin(all_dates)]
            if merged.empty:
                continue

            merged["valeur"]    = (merged["price"] * merged["quantite"]).round(2)
            merged["asset_id"]  = asset["id"]
            merged["nom"]       = asset["nom"]
            merged["categorie"] = asset["categorie"]
            parts.append(merged[["date", "asset_id", "nom", "categorie", "valeur"]])

    if not parts:
        return pd.DataFrame()

    return pd.concat(parts, ignore_index=True)


# ── Helpers privés ────────────────────────────────────────────────────────────

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