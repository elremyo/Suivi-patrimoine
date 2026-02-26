import os
import pandas as pd
from datetime import date
from pandas.errors import EmptyDataError
from constants import POSITIONS_PATH

COLUMNS = ["asset_id", "date", "quantite"]


def init_positions():
    if not os.path.exists(POSITIONS_PATH):
        pd.DataFrame(columns=COLUMNS).to_csv(POSITIONS_PATH, index=False)


def load_positions() -> pd.DataFrame:
    try:
        df = pd.read_csv(POSITIONS_PATH, parse_dates=["date"])
        if df.empty or list(df.columns) != COLUMNS:
            return pd.DataFrame(columns=COLUMNS)
        return df
    except (EmptyDataError, FileNotFoundError):
        return pd.DataFrame(columns=COLUMNS)


def record_position(asset_id: str, quantite: float, record_date: date | None = None):
    """
    Enregistre la quantité détenue pour un actif à une date donnée.
    Si un enregistrement existe déjà pour ce jour, il est écrasé.
    """
    d = pd.Timestamp(record_date or date.today())
    df = load_positions()

    if not df.empty:
        df = df[~((df["asset_id"] == asset_id) & (df["date"] == d))]

    new_row = pd.DataFrame([[asset_id, d, quantite]], columns=COLUMNS)
    df = pd.concat([df, new_row], ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["asset_id", "date"]).reset_index(drop=True)
    df.to_csv(POSITIONS_PATH, index=False)


def delete_asset_positions(asset_id: str):
    """Supprime toutes les positions d'un actif (utile à la suppression d'un actif)."""
    df = load_positions()
    if df.empty:
        return
    df = df[df["asset_id"] != asset_id].reset_index(drop=True)
    df.to_csv(POSITIONS_PATH, index=False)


def get_quantity_at(asset_id: str, at_date: pd.Timestamp, df_positions: pd.DataFrame) -> float | None:
    """
    Retourne la quantité détenue pour un actif à une date donnée.
    Utilise le dernier enregistrement connu avant ou égal à at_date.
    Retourne None si aucun enregistrement n'existe avant cette date.
    """
    asset_pos = df_positions[df_positions["asset_id"] == asset_id]
    past = asset_pos[asset_pos["date"] <= at_date]
    if past.empty:
        return None
    return float(past.sort_values("date").iloc[-1]["quantite"])


def get_all_asset_ids(df_positions: pd.DataFrame) -> list[str]:
    return df_positions["asset_id"].unique().tolist()