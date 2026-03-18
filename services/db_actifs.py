"""
db_actifs.py
──────────
Gestion des actifs et leurs spécificités (ticker, immobilier).
"""

import pandas as pd
from .db import db_readonly, db_connection

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
IMMO_EXTRA_COLUMNS = ["prix_achat", "emprunt_id", "type_bien", "adresse", "superficie_m2", "frais_notaire", "montant_travaux", "usage", "loyer_mensuel", "charges_mensuelles", "taxe_fonciere_annuelle"]

def load_assets() -> pd.DataFrame:
    """
    Retourne un DataFrame plat : id, nom, categorie, montant, ticker, quantite, pru, contrat_id.
    Pour l'immobilier, ajoute prix_achat, type_bien, adresse, superficie_m2, emprunt_id.
    """
    with db_readonly() as conn:
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

        q_immo = """
            SELECT actif_id, prix_achat, emprunt_id, type_bien, adresse, superficie_m2,
                   COALESCE(frais_notaire, 0) AS frais_notaire,
                   COALESCE(montant_travaux, 0) AS montant_travaux,
                   COALESCE(usage, 'locatif') AS usage,
                   COALESCE(loyer_mensuel, 0) AS loyer_mensuel,
                   COALESCE(charges_mensuelles, 0) AS charges_mensuelles,
                   COALESCE(taxe_fonciere_annuelle, 0) AS taxe_fonciere_annuelle
            FROM actifs_immobilier
        """

        try:
            df_immo = pd.read_sql_query(q_immo, conn)
        except pd.errors.DatabaseError:
            df_immo = pd.DataFrame()

    df["categorie"] = df["type"].map(TYPE_TO_CATEGORY)
    df["montant"] = df["montant_actuel"]
    df = df[["id", "nom", "categorie", "montant", "ticker", "quantite", "pru", "contrat_id"]]

    if not df_immo.empty and not df.empty:
        df = df.merge(df_immo, left_on="id", right_on="actif_id", how="left", suffixes=("", "_immo"))
        if "actif_id" in df.columns:
            df = df.drop(columns=["actif_id"])
        for col in ["prix_achat", "type_bien", "adresse", "superficie_m2", "emprunt_id", "frais_notaire", "montant_travaux", "usage", "loyer_mensuel", "charges_mensuelles", "taxe_fonciere_annuelle"]:
            if col not in df.columns:
                df[col] = None

    return df.reset_index(drop=True)


def save_assets(df: pd.DataFrame) -> None:
    """Persiste le DataFrame plat dans les tables actifs, actifs_ticker, actifs_immobilier."""
    if df.empty:
        with db_connection() as conn:
            conn.execute("DELETE FROM actifs_ticker")
            conn.execute("DELETE FROM actifs_immobilier")
            conn.execute("DELETE FROM actifs")
        return

    with db_connection() as conn:
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
                frais_notaire = row.get("frais_notaire")
                frais_notaire = float(frais_notaire) if frais_notaire is not None and not pd.isna(frais_notaire) else 0.0
                montant_travaux = row.get("montant_travaux")
                montant_travaux = float(montant_travaux) if montant_travaux is not None and not pd.isna(montant_travaux) else 0.0
                usage = row.get("usage")
                usage = str(usage) if usage in ("residence_principale", "locatif") else "locatif"
                loyer_mensuel = row.get("loyer_mensuel")
                loyer_mensuel = float(loyer_mensuel) if loyer_mensuel is not None and not pd.isna(loyer_mensuel) else 0.0
                charges_mensuelles = row.get("charges_mensuelles")
                charges_mensuelles = float(charges_mensuelles) if charges_mensuelles is not None and not pd.isna(charges_mensuelles) else 0.0
                taxe_fonciere = row.get("taxe_fonciere_annuelle")
                taxe_fonciere = float(taxe_fonciere) if taxe_fonciere is not None and not pd.isna(taxe_fonciere) else 0.0

                conn.execute(
                    """
                    INSERT INTO actifs_immobilier (actif_id, prix_achat, emprunt_id, type_bien, adresse, superficie_m2, frais_notaire, montant_travaux, usage, loyer_mensuel, charges_mensuelles, taxe_fonciere_annuelle)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(actif_id) DO UPDATE SET
                        prix_achat = excluded.prix_achat,
                        emprunt_id = excluded.emprunt_id,
                        type_bien = excluded.type_bien,
                        adresse = excluded.adresse,
                        superficie_m2 = excluded.superficie_m2,
                        frais_notaire = excluded.frais_notaire,
                        montant_travaux = excluded.montant_travaux,
                        usage = excluded.usage,
                        loyer_mensuel = excluded.loyer_mensuel,
                        charges_mensuelles = excluded.charges_mensuelles,
                        taxe_fonciere_annuelle = excluded.taxe_fonciere_annuelle
                    """,
                    (aid, prix_achat, emprunt_id, type_bien, adresse, superficie, frais_notaire, montant_travaux, usage, loyer_mensuel, charges_mensuelles, taxe_fonciere),
                )
            else:
                conn.execute("DELETE FROM actifs_immobilier WHERE actif_id = ?", (aid,))



def get_total_by_type() -> pd.DataFrame:
    with db_readonly() as conn:
        df = pd.read_sql_query(
            "SELECT type, SUM(montant_actuel) AS total FROM actifs GROUP BY type", conn,
        )
        df["categorie"] = df["type"].map(TYPE_TO_CATEGORY)
        return df[["categorie", "total"]].rename(columns={"total": "montant"})


def get_total() -> float:
    with db_readonly() as conn:
        cur = conn.execute("SELECT COALESCE(SUM(montant_actuel), 0) FROM actifs")
        return float(cur.fetchone()[0])
