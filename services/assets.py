import uuid
import pandas as pd
from services.storage import load_assets


def get_assets() -> pd.DataFrame:
    return load_assets()


def add_asset(df: pd.DataFrame, nom: str, categorie: str, montant: float,
              ticker: str = "", quantite: float = 0.0, pru: float = 0.0) -> pd.DataFrame:
    # Pour les actifs auto, le montant initial = PRU × quantité en attendant le premier refresh
    if ticker and quantite > 0 and pru > 0:
        montant = round(pru * quantite, 2)
    asset_id = str(uuid.uuid4())
    new_row = pd.DataFrame(
        [[asset_id, nom, categorie, montant, ticker, quantite, pru]],
        columns=df.columns
    )
    # Évite le FutureWarning pandas : concat avec un DataFrame vide
    # se comportera différemment dans les prochaines versions
    if df.empty:
        df = new_row.reset_index(drop=True)
    else:
        df = pd.concat([df, new_row], ignore_index=True)
    return df


def update_asset(df: pd.DataFrame, idx: int, nom: str, categorie: str, montant: float,
                 ticker: str = "", quantite: float = 0.0, pru: float = 0.0) -> pd.DataFrame:
    df.loc[idx, "nom"] = nom
    df.loc[idx, "categorie"] = categorie
    df.loc[idx, "montant"] = montant
    df.loc[idx, "ticker"] = ticker
    df.loc[idx, "quantite"] = quantite
    df.loc[idx, "pru"] = pru
    return df


def delete_asset(df: pd.DataFrame, idx: int) -> pd.DataFrame:
    df = df.drop(index=idx).reset_index(drop=True)
    return df


def compute_total(df: pd.DataFrame) -> float:
    return df["montant"].sum()


def compute_by_category(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["categorie", "montant", "pourcentage"])

    grouped = df.groupby("categorie")["montant"].sum()
    total = grouped.sum()

    result = grouped.reset_index()
    result.columns = ["categorie", "montant"]
    result["pourcentage"] = (result["montant"] / total * 100).round(2)

    return result.sort_values("montant", ascending=False).reset_index(drop=True)