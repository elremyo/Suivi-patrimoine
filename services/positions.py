import pandas as pd

from services import db


def init_positions():
    """Les tables sont créées par init_storage (db.init_db())."""
    pass


def load_positions() -> pd.DataFrame:
    from services.db_positions import load_positions
    return load_positions()


def record_position(asset_id: str, quantite: float, record_date=None):
    """
    Enregistre la quantité détenue pour un actif à une date donnée.
    Si un enregistrement existe déjà pour ce jour, il est écrasé.
    """
    from services.db_positions import record_position
    record_position(asset_id, quantite, record_date)


def delete_asset_positions(asset_id: str):
    """Supprime toutes les positions d'un actif (utile à la suppression d'un actif)."""
    from services.db_positions import delete_asset_positions
    delete_asset_positions(asset_id)


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
