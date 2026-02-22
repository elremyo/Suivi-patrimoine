import os
import pandas as pd
from datetime import date
from pandas.errors import EmptyDataError

HISTORIQUE_PATH = "data/historique.csv"
COLUMNS = ["date", "categorie", "montant"]


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


def save_snapshot(df_assets: pd.DataFrame, snapshot_date: date | None = None) -> bool:
    """
    Enregistre l'état actuel des actifs groupés par catégorie.
    Si un snapshot existe déjà pour cette date, il est remplacé.
    Retourne True si sauvegardé, False si df_assets est vide.
    """
    if df_assets.empty:
        return False

    d = snapshot_date or date.today()

    grouped = (
        df_assets.groupby("categorie")["montant"]
        .sum()
        .reset_index()
    )
    grouped.insert(0, "date", d)
    grouped.columns = COLUMNS

    df_hist = load_historique()

    # Supprime l'éventuel snapshot existant pour cette date
    df_hist = df_hist[df_hist["date"] != pd.Timestamp(d)] if not df_hist.empty else df_hist

    df_hist = pd.concat([df_hist, grouped], ignore_index=True)
    df_hist["date"] = pd.to_datetime(df_hist["date"])
    df_hist = df_hist.sort_values("date").reset_index(drop=True)
    df_hist.to_csv(HISTORIQUE_PATH, index=False)
    return True


def delete_snapshot(df_hist: pd.DataFrame, snapshot_date: date) -> pd.DataFrame:
    df_hist = df_hist[df_hist["date"] != pd.Timestamp(snapshot_date)].reset_index(drop=True)
    df_hist.to_csv(HISTORIQUE_PATH, index=False)
    return df_hist


def get_total_evolution(df_hist: pd.DataFrame) -> pd.DataFrame:
    """Retourne une série date → total patrimoine."""
    if df_hist.empty:
        return pd.DataFrame(columns=["date", "total"])
    result = df_hist.groupby("date")["montant"].sum().reset_index()
    result.columns = ["date", "total"]
    return result.sort_values("date")


def get_category_evolution(df_hist: pd.DataFrame) -> pd.DataFrame:
    """Retourne un pivot date × catégorie."""
    if df_hist.empty:
        return pd.DataFrame()
    pivot = df_hist.pivot_table(
        index="date", columns="categorie", values="montant", aggfunc="sum"
    ).fillna(0)
    pivot.index = pd.to_datetime(pivot.index)
    return pivot.sort_index()


def get_snapshot_table(df_hist: pd.DataFrame) -> pd.DataFrame:
    """Retourne un tableau récapitulatif par snapshot (date × catégorie + total)."""
    if df_hist.empty:
        return pd.DataFrame()
    pivot = get_category_evolution(df_hist).copy()
    pivot["Total"] = pivot.sum(axis=1)
    pivot.index = pivot.index.strftime("%d/%m/%Y")
    pivot.index.name = "Date"
    return pivot