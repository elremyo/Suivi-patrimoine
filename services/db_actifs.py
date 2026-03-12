"""
db_actifs.py
──────────
Gestion des actifs et leurs spécificités (ticker, immobilier).
"""

import pandas as pd
from .db import get_conn

# Mapping catégorie (UI / CSV) <-> type (DB)
CATEGORY_TO_TYPE = {
    "Actions & Fonds": "action",
    "Crypto": "crypto",
    "Livrets": "livret",
    "Immobilier": "immobilier",
    "Fonds euros": "fonds_euro",
    "Compte": "compte",
}
TYPE_TO_CATEGORY = {v: k for k, v in CATEGORY_TO_TYPE.items()}

ASSETS_FLAT_COLUMNS = [
    "id", "nom", "categorie", "montant", "ticker", "quantite", "pru",
    "contrat_id",
]
IMMO_EXTRA_COLUMNS = ["prix_achat", "emprunt_id", "type_bien", "adresse", "superficie_m2"]


def load_assets() -> pd.DataFrame:
    """
    Retourne un DataFrame plat : id, nom, categorie, montant, ticker, quantite, pru, contrat_id.
    Pour l'immobilier, ajoute prix_achat, type_bien, adresse, superficie_m2, emprunt_id.
    """
    conn = get_conn()
    try:
        q = """
        SELECT a.id, a.type, a.nom, a.montant_actuel, a.contrat_id,
               COALESCE(t.ticker, '') AS ticker,
               COALESCE(t.quantite, 0) AS quantite,
               COALESCE(t.pru, 0) AS pru
        FROM actifs a
        LEFT JOIN actifs_ticker t ON t.actif_id = a.id
        ORDER BY a.type, a.nom
        """
        df = pd.read_sql_query(q, conn)

        q_immo = "SELECT actif_id, prix_achat, emprunt_id, type_bien, adresse, superficie_m2 FROM actifs_immobilier"
        try:
            df_immo = pd.read_sql_query(q_immo, conn)
        except pd.errors.DatabaseError:
            df_immo = pd.DataFrame()

        conn.close()
    except Exception:
        conn.close()
        raise

    df["categorie"] = df["type"].map(TYPE_TO_CATEGORY)
    df["montant"] = df["montant_actuel"]
    df = df[["id", "nom", "categorie", "montant", "ticker", "quantite", "pru", "contrat_id"]]

    if not df_immo.empty and not df.empty:
        df = df.merge(df_immo, left_on="id", right_on="actif_id", how="left", suffixes=("", "_immo"))
        if "actif_id" in df.columns:
            df = df.drop(columns=["actif_id"])
        for col in ["prix_achat", "type_bien", "adresse", "superficie_m2", "emprunt_id"]:
            if col not in df.columns:
                df[col] = None

    return df.reset_index(drop=True)


def save_assets(df: pd.DataFrame) -> None:
    """Persiste le DataFrame plat dans les tables actifs, actifs_ticker, actifs_immobilier."""
    if df.empty:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM actifs_ticker")
            conn.execute("DELETE FROM actifs_immobilier")
            conn.execute("DELETE FROM actifs")
            conn.commit()
        finally:
            conn.close()
        return

    conn = get_conn()
    try:
        ids_in_df = set(df["id"].astype(str))
        cur = conn.execute("SELECT id FROM actifs")
        existing_ids = {row[0] for row in cur.fetchall()}
        for aid in existing_ids - ids_in_df:
            conn.execute("DELETE FROM actifs WHERE id = ?", (aid,))

        for _, row in df.iterrows():
            aid = str(row["id"])
            type_ = CATEGORY_TO_TYPE.get(str(row["categorie"]), "livret")
            nom = str(row["nom"])
            montant = float(row["montant"])
            contrat_id = row.get("contrat_id")
            contrat_id = None if (contrat_id is None or (isinstance(contrat_id, float) and pd.isna(contrat_id)) or contrat_id == "") else str(contrat_id)

            conn.execute(
                """
                INSERT INTO actifs (id, type, nom, montant_actuel, contrat_id, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(id) DO UPDATE SET
                    type = excluded.type,
                    nom = excluded.nom,
                    montant_actuel = excluded.montant_actuel,
                    contrat_id = excluded.contrat_id,
                    updated_at = datetime('now')
                """,
                (aid, type_, nom, montant, contrat_id),
            )

            if type_ in ("action", "crypto"):
                ticker = str(row.get("ticker", "") or "")
                quantite = float(row.get("quantite", 0) or 0)
                pru = float(row.get("pru", 0) or 0)
                conn.execute(
                    """
                    INSERT INTO actifs_ticker (actif_id, ticker, quantite, pru)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(actif_id) DO UPDATE SET ticker = excluded.ticker, quantite = excluded.quantite, pru = excluded.pru
                    """,
                    (aid, ticker, quantite, pru),
                )
            else:
                conn.execute("DELETE FROM actifs_ticker WHERE actif_id = ?", (aid,))

            if type_ == "immobilier":
                raw_prix = row.get("prix_achat", row.get("montant", 0))
                prix_achat = 0.0 if (raw_prix is None or (isinstance(raw_prix, float) and pd.isna(raw_prix))) else float(raw_prix)
                emprunt_id = row.get("emprunt_id")
                if pd.isna(emprunt_id) or emprunt_id == "":
                    emprunt_id = None
                else:
                    emprunt_id = str(emprunt_id)
                type_bien = str(row.get("type_bien", "autre") or "autre")
                adresse = row.get("adresse")
                adresse = str(adresse) if adresse is not None and not pd.isna(adresse) else None
                superficie = row.get("superficie_m2")
                superficie = float(superficie) if superficie is not None and not pd.isna(superficie) else None
                conn.execute(
                    """
                    INSERT INTO actifs_immobilier (actif_id, prix_achat, emprunt_id, type_bien, adresse, superficie_m2)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(actif_id) DO UPDATE SET
                        prix_achat = excluded.prix_achat,
                        emprunt_id = excluded.emprunt_id,
                        type_bien = excluded.type_bien,
                        adresse = excluded.adresse,
                        superficie_m2 = excluded.superficie_m2
                    """,
                    (aid, prix_achat, emprunt_id, type_bien, adresse, superficie),
                )
            else:
                conn.execute("DELETE FROM actifs_immobilier WHERE actif_id = ?", (aid,))

        conn.commit()
    finally:
        conn.close()


def get_total_by_type() -> pd.DataFrame:
    conn = get_conn()
    try:
        df = pd.read_sql_query(
            "SELECT type, SUM(montant_actuel) AS total FROM actifs GROUP BY type", conn,
        )
        df["categorie"] = df["type"].map(TYPE_TO_CATEGORY)
        return df[["categorie", "total"]].rename(columns={"total": "montant"})
    finally:
        conn.close()


def get_total() -> float:
    conn = get_conn()
    try:
        cur = conn.execute("SELECT COALESCE(SUM(montant_actuel), 0) FROM actifs")
        return float(cur.fetchone()[0])
    finally:
        conn.close()
