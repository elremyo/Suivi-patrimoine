import os
import pandas as pd
from datetime import date
from pandas.errors import EmptyDataError
from constants import HISTORIQUE_PATH

COLUMNS = ["asset_id", "date", "montant"]


def init_historique():
    if not os.path.exists(HISTORIQUE_PATH):
        pd.DataFrame(columns=COLUMNS).to_csv(HISTORIQUE_PATH, index=False)


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
    df = pd.concat([df, new_row], ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["asset_id", "date"]).reset_index(drop=True)
    df.to_csv(HISTORIQUE_PATH, index=False)


def delete_asset_history(asset_id: str):
    """Supprime tout l'historique d'un actif (utile à la suppression d'un actif)."""
    df = load_historique()
    if df.empty:
        return
    df = df[df["asset_id"] != asset_id].reset_index(drop=True)
    df.to_csv(HISTORIQUE_PATH, index=False)


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


def build_total_evolution(
    df_assets: pd.DataFrame,
    df_hist: pd.DataFrame,
    df_positions: pd.DataFrame,
    df_prices: pd.DataFrame,
    categories_auto: set,
) -> pd.DataFrame:
    """
    Reconstruit la courbe d'évolution du patrimoine total en fusionnant :
    - les actifs auto  : prix historiques yfinance × quantité connue à chaque date
    - les actifs manuels : historique CSV (dernier montant connu à chaque date)

    df_prices : DataFrame pivot date × ticker (prix de clôture historiques, depuis yfinance)
    df_positions : journal des quantités (asset_id, date, quantite)

    Retourne un DataFrame { date, total }.
    """
    if df_assets.empty:
        return pd.DataFrame(columns=["date", "total"])

    all_dates = _collect_all_dates(df_hist, df_prices)
    if all_dates.empty:
        return pd.DataFrame(columns=["date", "total"])

    earliest = _earliest_known_date(df_hist, df_positions)
    if earliest is not None:
        all_dates = all_dates[all_dates >= earliest]

    records = []
    for d in all_dates:
        total = 0.0
        has_value = False
        for _, asset in df_assets.iterrows():
            if asset["categorie"] in categories_auto and asset["ticker"]:
                val = _auto_value_at(asset, d, df_positions, df_prices)
            else:
                val = get_montant_at(asset["id"], d, df_hist)
            if val is not None:
                total += val
                has_value = True
        if has_value:
            records.append({"date": d, "total": total})

    result = pd.DataFrame(records)
    return result.sort_values("date").reset_index(drop=True)


def build_category_evolution(
    df_assets: pd.DataFrame,
    df_hist: pd.DataFrame,
    df_positions: pd.DataFrame,
    df_prices: pd.DataFrame,
    categories_auto: set,
) -> pd.DataFrame:
    """
    Même logique que build_total_evolution mais retourne un pivot date × catégorie.
    """
    if df_assets.empty:
        return pd.DataFrame()

    all_dates = _collect_all_dates(df_hist, df_prices)
    if all_dates.empty:
        return pd.DataFrame()

    earliest = _earliest_known_date(df_hist, df_positions)
    if earliest is not None:
        all_dates = all_dates[all_dates >= earliest]

    records = []
    for d in all_dates:
        row = {"date": d}
        has_value = False
        for cat in df_assets["categorie"].unique():
            cat_assets = df_assets[df_assets["categorie"] == cat]
            total_cat = 0.0
            for _, asset in cat_assets.iterrows():
                if asset["categorie"] in categories_auto and asset["ticker"]:
                    val = _auto_value_at(asset, d, df_positions, df_prices)
                else:
                    val = get_montant_at(asset["id"], d, df_hist)
                if val is not None:
                    total_cat += val
                    has_value = True
            row[cat] = total_cat
        if has_value:
            records.append(row)

    pivot = pd.DataFrame(records).set_index("date").sort_index()
    return pivot


def build_asset_evolution(
    df_assets: pd.DataFrame,
    df_hist: pd.DataFrame,
    df_positions: pd.DataFrame,
    df_prices: pd.DataFrame,
    categories_auto: set,
) -> pd.DataFrame:
    """
    Même logique que build_category_evolution mais retourne un pivot date × nom d'actif.
    La colonne est le nom de l'actif (pas l'id).
    """
    if df_assets.empty:
        return pd.DataFrame()

    all_dates = _collect_all_dates(df_hist, df_prices)
    if all_dates.empty:
        return pd.DataFrame()

    earliest = _earliest_known_date(df_hist, df_positions)
    if earliest is not None:
        all_dates = all_dates[all_dates >= earliest]

    records = []
    for d in all_dates:
        row = {"date": d}
        has_value = False
        for _, asset in df_assets.iterrows():
            if asset["categorie"] in categories_auto and asset["ticker"]:
                val = _auto_value_at(asset, d, df_positions, df_prices)
            else:
                val = get_montant_at(asset["id"], d, df_hist)
            if val is not None:
                row[asset["nom"]] = val
                has_value = True
            else:
                row[asset["nom"]] = 0.0
        if has_value:
            records.append(row)

    pivot = pd.DataFrame(records).set_index("date").sort_index()
    return pivot


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


def _auto_value_at(
    asset: pd.Series,
    at_date: pd.Timestamp,
    df_positions: pd.DataFrame,
    df_prices: pd.DataFrame,
) -> float | None:
    """Calcule la valeur d'un actif auto à une date : prix × quantité connue."""
    from services.positions import get_quantity_at

    ticker = asset["ticker"]
    quantite = get_quantity_at(asset["id"], at_date, df_positions)
    if quantite is None:
        return None

    if df_prices.empty or ticker not in df_prices.columns:
        return None

    prices_series = df_prices[ticker].dropna()
    past_prices = prices_series[prices_series.index.normalize() <= at_date.normalize()]
    if past_prices.empty:
        return None

    price = float(past_prices.iloc[-1])
    return round(price * quantite, 2)