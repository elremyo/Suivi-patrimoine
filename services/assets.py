import pandas as pd
from services.storage import load_assets, save_assets


def get_assets() -> pd.DataFrame:
    return load_assets()


def add_asset(df: pd.DataFrame, nom: str, categorie: str, montant: float, notes: str = "") -> pd.DataFrame:
    new_row = pd.DataFrame([[nom, categorie, montant, notes]], columns=df.columns)
    df = pd.concat([df, new_row], ignore_index=True)
    save_assets(df)
    return df


def update_asset(df: pd.DataFrame, idx: int, nom: str, categorie: str, montant: float, notes: str = "") -> pd.DataFrame:
    df.loc[idx, "nom"] = nom
    df.loc[idx, "categorie"] = categorie
    df.loc[idx, "montant"] = montant
    df.loc[idx, "notes"] = notes
    save_assets(df)
    return df


def delete_asset(df: pd.DataFrame, idx: int) -> pd.DataFrame:
    df = df.drop(index=idx).reset_index(drop=True)
    save_assets(df)
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