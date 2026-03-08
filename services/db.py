"""
db.py
─────
Couche d'accès SQLite pour le suivi de patrimoine.
"""

import os
import sqlite3
import uuid
from datetime import date
from pathlib import Path

import pandas as pd

from constants import DB_PATH

# Mapping catégorie (UI / CSV) <-> type (DB)
CATEGORY_TO_TYPE = {
    "Actions & Fonds": "action",
    "Crypto": "crypto",
    "Livrets": "livret",
    "Immobilier": "immobilier",
    "Fonds euros": "fonds_euro",
}
TYPE_TO_CATEGORY = {v: k for k, v in CATEGORY_TO_TYPE.items()}

ASSETS_FLAT_COLUMNS = [
    "id", "nom", "categorie", "montant", "ticker", "quantite", "pru",
    "courtier", "enveloppe", "contrat_id",
]
IMMO_EXTRA_COLUMNS = ["prix_achat", "emprunt_id", "type_bien", "adresse", "superficie_m2"]


def _schema_path() -> str:
    return str(Path(__file__).resolve().parent.parent / "schema" / "schema.sql")


def get_conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    """Crée le fichier DB et les tables s'ils n'existent pas.
    Applique aussi les migrations nécessaires sur une base existante."""
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    schema_path = _schema_path()
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schéma introuvable : {schema_path}")
    with open(schema_path, encoding="utf-8") as f:
        sql = f.read()
    conn = get_conn()
    try:
        conn.executescript(sql)
        conn.commit()
        _migrate(conn)
    finally:
        conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    """Applique les migrations incrémentales sur une base existante."""
    # Ajout de contrat_id dans actifs si absent (base existante avant cette feature)
    cols = [row[1] for row in conn.execute("PRAGMA table_info(actifs)").fetchall()]
    if "contrat_id" not in cols:
        conn.execute("ALTER TABLE actifs ADD COLUMN contrat_id TEXT REFERENCES contrats(id) ON DELETE SET NULL")
        conn.commit()


# ── Contrats ──────────────────────────────────────────────────────────────────

def load_contrats() -> pd.DataFrame:
    """Retourne tous les contrats avec colonnes : id, etablissement, enveloppe."""
    conn = get_conn()
    try:
        df = pd.read_sql_query(
            "SELECT id, etablissement, enveloppe FROM contrats ORDER BY etablissement, enveloppe",
            conn,
        )
        return df
    finally:
        conn.close()


def get_or_create_contrat(etablissement: str, enveloppe: str) -> str:
    """
    Retourne l'id du contrat correspondant à (etablissement, enveloppe).
    Le crée s'il n'existe pas encore.
    """
    etablissement = etablissement.strip()
    enveloppe = enveloppe.strip()
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id FROM contrats WHERE etablissement = ? AND enveloppe = ?",
            (etablissement, enveloppe),
        ).fetchone()
        if row:
            return row[0]
        contrat_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO contrats (id, etablissement, enveloppe) VALUES (?, ?, ?)",
            (contrat_id, etablissement, enveloppe),
        )
        conn.commit()
        return contrat_id
    finally:
        conn.close()


def add_contrat(etablissement: str, enveloppe: str) -> tuple[bool, str, str | None]:
    """
    Crée un nouveau contrat. Retourne (succès, message, contrat_id).
    Échoue si le couple (etablissement, enveloppe) existe déjà.
    """
    etablissement = etablissement.strip()
    enveloppe = enveloppe.strip()
    if not etablissement or not enveloppe:
        return False, "L'établissement et l'enveloppe sont obligatoires.", None
    conn = get_conn()
    try:
        contrat_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO contrats (id, etablissement, enveloppe) VALUES (?, ?, ?)",
            (contrat_id, etablissement, enveloppe),
        )
        conn.commit()
        return True, f"Contrat « {etablissement} — {enveloppe} » ajouté.", contrat_id
    except sqlite3.IntegrityError:
        return False, f"« {etablissement} — {enveloppe} » existe déjà.", None
    finally:
        conn.close()


def update_contrat(contrat_id: str, etablissement: str, enveloppe: str) -> tuple[bool, str]:
    """Met à jour un contrat existant."""
    etablissement = etablissement.strip()
    enveloppe = enveloppe.strip()
    if not etablissement or not enveloppe:
        return False, "L'établissement et l'enveloppe sont obligatoires."
    conn = get_conn()
    try:
        # Vérifier unicité sur les autres contrats
        row = conn.execute(
            "SELECT id FROM contrats WHERE etablissement = ? AND enveloppe = ? AND id != ?",
            (etablissement, enveloppe, contrat_id),
        ).fetchone()
        if row:
            return False, f"« {etablissement} — {enveloppe} » existe déjà."
        conn.execute(
            "UPDATE contrats SET etablissement = ?, enveloppe = ? WHERE id = ?",
            (etablissement, enveloppe, contrat_id),
        )
        conn.commit()
        return True, f"Contrat mis à jour : « {etablissement} — {enveloppe} »."
    finally:
        conn.close()


def delete_contrat(contrat_id: str) -> tuple[bool, str]:
    """
    Supprime un contrat seulement s'il n'est utilisé par aucun actif.
    """
    conn = get_conn()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM actifs WHERE contrat_id = ?", (contrat_id,)
        ).fetchone()[0]
        if count > 0:
            return False, f"Ce contrat est utilisé par {count} actif(s) — modifie-les d'abord."
        conn.execute("DELETE FROM contrats WHERE id = ?", (contrat_id,))
        conn.commit()
        return True, "Contrat supprimé."
    finally:
        conn.close()


# ── Actifs ───────────────────────────────────────────────────────────────────

def load_assets() -> pd.DataFrame:
    """
    Retourne un DataFrame plat : id, nom, categorie, montant, ticker, quantite, pru,
    courtier, enveloppe, contrat_id.
    Pour l'immobilier, ajoute prix_achat, type_bien, adresse, superficie_m2, emprunt_id.
    """
    conn = get_conn()
    try:
        q = """
        SELECT a.id, a.type, a.nom, a.montant_actuel, a.courtier, a.enveloppe,
               a.contrat_id,
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
    df = df[["id", "nom", "categorie", "montant", "ticker", "quantite", "pru", "courtier", "enveloppe", "contrat_id"]]

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
            courtier = str(row.get("courtier", "") or "")
            enveloppe = str(row.get("enveloppe", "") or "")
            contrat_id = row.get("contrat_id")
            contrat_id = None if (contrat_id is None or (isinstance(contrat_id, float) and pd.isna(contrat_id)) or contrat_id == "") else str(contrat_id)

            conn.execute(
                """
                INSERT INTO actifs (id, type, nom, montant_actuel, courtier, enveloppe, contrat_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(id) DO UPDATE SET
                    type = excluded.type,
                    nom = excluded.nom,
                    montant_actuel = excluded.montant_actuel,
                    courtier = excluded.courtier,
                    enveloppe = excluded.enveloppe,
                    contrat_id = excluded.contrat_id,
                    updated_at = datetime('now')
                """,
                (aid, type_, nom, montant, courtier, enveloppe, contrat_id),
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


def get_assets_by_type(asset_type: str) -> pd.DataFrame:
    df = load_assets()
    type_to_cat = TYPE_TO_CATEGORY.get(asset_type, asset_type)
    return df[df["categorie"] == type_to_cat].copy()


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


# ── Historique ────────────────────────────────────────────────────────────────

def load_historique() -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT asset_id, date, montant FROM historique ORDER BY asset_id, date",
        get_conn(),
    )
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def record_montant(asset_id: str, montant: float, record_date: date | None = None) -> None:
    d = (record_date or date.today()).isoformat()
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO historique (asset_id, date, montant) VALUES (?, ?, ?)",
            (asset_id, d, float(montant)),
        )
        conn.commit()
    finally:
        conn.close()


def delete_asset_history(asset_id: str) -> None:
    conn = get_conn()
    try:
        conn.execute("DELETE FROM historique WHERE asset_id = ?", (asset_id,))
        conn.commit()
    finally:
        conn.close()


# ── Positions ────────────────────────────────────────────────────────────────

def load_positions() -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT asset_id, date, quantite FROM positions ORDER BY asset_id, date",
        get_conn(),
    )
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def record_position(asset_id: str, quantite: float, record_date: date | None = None) -> None:
    d = (record_date or date.today()).isoformat()
    conn = get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO positions (asset_id, date, quantite) VALUES (?, ?, ?)",
            (asset_id, d, float(quantite)),
        )
        conn.commit()
    finally:
        conn.close()


def delete_asset_positions(asset_id: str) -> None:
    conn = get_conn()
    try:
        conn.execute("DELETE FROM positions WHERE asset_id = ?", (asset_id,))
        conn.commit()
    finally:
        conn.close()


# ── Emprunts ───────────────────────────────────────────────────────────────────

def _compute_capital_restant_du(
    montant_emprunte: float,
    taux_annuel: float,
    mensualite: float,
    date_debut,
    duree_mois: int,
    as_of_date: date | None = None,
) -> float:
    if as_of_date is None:
        as_of_date = date.today()
    if isinstance(date_debut, str):
        debut = pd.Timestamp(date_debut).date()
    elif isinstance(date_debut, pd.Timestamp):
        debut = date_debut.date()
    elif hasattr(date_debut, "date"):
        debut = date_debut.date()
    else:
        debut = date_debut
    if isinstance(as_of_date, pd.Timestamp):
        as_of_date = as_of_date.date()
    months_elapsed = (as_of_date.year - debut.year) * 12 + (as_of_date.month - debut.month)
    if debut.day > as_of_date.day:
        months_elapsed -= 1
    months_elapsed = max(0, min(months_elapsed, duree_mois))
    if months_elapsed >= duree_mois:
        return 0.0
    P = float(montant_emprunte)
    M = float(mensualite)
    r = float(taux_annuel) / 100.0 / 12.0
    k = months_elapsed
    if abs(r) < 1e-9:
        balance = P - M * k
    else:
        balance = P * ((1 + r) ** k) - M * (((1 + r) ** k - 1) / r)
    return round(max(0.0, balance), 2)


def load_emprunts(as_of_date: date | None = None) -> pd.DataFrame:
    conn = get_conn()
    try:
        df = pd.read_sql_query(
            """SELECT id, nom, montant_emprunte, taux_annuel, mensualite, duree_mois, date_debut, date_fin
               FROM emprunts ORDER BY nom""",
            conn,
        )
        if not df.empty:
            df["date_debut"] = pd.to_datetime(df["date_debut"], errors="coerce")
            df["date_fin"] = pd.to_datetime(df["date_fin"], errors="coerce")
            as_of = as_of_date or date.today()
            for i in df.index:
                try:
                    df.loc[i, "capital_restant_du"] = _compute_capital_restant_du(
                        float(df.loc[i, "montant_emprunte"]),
                        float(df.loc[i, "taux_annuel"]),
                        float(df.loc[i, "mensualite"]),
                        df.loc[i, "date_debut"],
                        int(df.loc[i, "duree_mois"]),
                        as_of,
                    )
                except (TypeError, ValueError):
                    df.loc[i, "capital_restant_du"] = 0.0
        return df
    finally:
        conn.close()


def create_emprunt(nom, montant_emprunte, taux_annuel, mensualite, duree_mois, date_debut, date_fin=None) -> str:
    emprunt_id = str(uuid.uuid4())
    conn = get_conn()
    try:
        conn.execute(
            """INSERT INTO emprunts (id, nom, montant_emprunte, taux_annuel, mensualite, duree_mois, date_debut, date_fin)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (emprunt_id, nom.strip(), float(montant_emprunte), float(taux_annuel), float(mensualite), int(duree_mois),
             date_debut if isinstance(date_debut, str) else pd.Timestamp(date_debut).strftime("%Y-%m-%d"),
             date_fin if date_fin is None or (isinstance(date_fin, str) and not date_fin.strip()) else (date_fin if isinstance(date_fin, str) else pd.Timestamp(date_fin).strftime("%Y-%m-%d"))),
        )
        conn.commit()
        return emprunt_id
    finally:
        conn.close()


def update_emprunt(emprunt_id, nom, montant_emprunte, taux_annuel, mensualite, duree_mois, date_debut, date_fin=None) -> None:
    conn = get_conn()
    try:
        conn.execute(
            """UPDATE emprunts SET nom = ?, montant_emprunte = ?, taux_annuel = ?, mensualite = ?, duree_mois = ?,
               date_debut = ?, date_fin = ?, updated_at = datetime('now') WHERE id = ?""",
            (nom.strip(), float(montant_emprunte), float(taux_annuel), float(mensualite), int(duree_mois),
             date_debut if isinstance(date_debut, str) else pd.Timestamp(date_debut).strftime("%Y-%m-%d"),
             date_fin if date_fin is None or (isinstance(date_fin, str) and not date_fin.strip()) else (date_fin if isinstance(date_fin, str) else pd.Timestamp(date_fin).strftime("%Y-%m-%d")),
             emprunt_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_emprunt(emprunt_id: str) -> None:
    conn = get_conn()
    try:
        conn.execute("DELETE FROM emprunts WHERE id = ?", (emprunt_id,))
        conn.commit()
    finally:
        conn.close()


def get_total_emprunts(as_of_date: date | None = None) -> float:
    df = load_emprunts(as_of_date=as_of_date)
    if df.empty:
        return 0.0
    return float(df["capital_restant_du"].fillna(0).sum())


# ── Référentiel ───────────────────────────────────────────────────────────────

def load_referentiel() -> pd.DataFrame:
    conn = get_conn()
    try:
        df = pd.read_sql_query(
            "SELECT kind AS type, value AS valeur FROM referentiel ORDER BY kind, value", conn,
        )
        return df
    finally:
        conn.close()


def init_referentiel_from_assets(df_assets: pd.DataFrame | None) -> None:
    from constants import ENVELOPPES
    conn = get_conn()
    try:
        cur = conn.execute("SELECT COUNT(*) FROM referentiel")
        if cur.fetchone()[0] > 0:
            return
        rows = []
        if df_assets is not None and not df_assets.empty:
            for courtier in df_assets["courtier"].dropna().unique():
                c = str(courtier).strip()
                if c:
                    rows.append(("courtier", c))
        for env in ENVELOPPES:
            rows.append(("enveloppe", env))
        for kind, value in rows:
            conn.execute("INSERT OR IGNORE INTO referentiel (kind, value) VALUES (?, ?)", (kind, value))
        conn.commit()
    finally:
        conn.close()


def add_courtier(value: str) -> tuple[bool, str]:
    value = value.strip()
    if not value:
        return False, "Le nom du courtier ne peut pas être vide."
    conn = get_conn()
    try:
        conn.execute("INSERT INTO referentiel (kind, value) VALUES ('courtier', ?)", (value,))
        conn.commit()
        return True, f"Courtier « {value} » ajouté."
    except sqlite3.IntegrityError:
        return False, f"« {value} » existe déjà."
    finally:
        conn.close()


def delete_courtier(value: str, df_assets: pd.DataFrame) -> tuple[bool, str]:
    if not df_assets.empty:
        used = (df_assets["courtier"].astype(str).str.strip() == value).any()
        if used:
            return False, f"« {value} » est encore utilisé par un actif."
    conn = get_conn()
    try:
        conn.execute("DELETE FROM referentiel WHERE kind = 'courtier' AND value = ?", (value,))
        conn.commit()
        return True, f"Courtier « {value} » supprimé."
    finally:
        conn.close()


def rename_courtier(ancien: str, nouveau: str, df_assets: pd.DataFrame) -> tuple[bool, str, pd.DataFrame]:
    nouveau = nouveau.strip()
    if not nouveau:
        return False, "Le nouveau nom ne peut pas être vide.", df_assets
    if nouveau == ancien:
        return False, "Le nouveau nom est identique à l'ancien.", df_assets
    conn = get_conn()
    try:
        cur = conn.execute("SELECT 1 FROM referentiel WHERE kind = 'courtier' AND value = ?", (nouveau,))
        if cur.fetchone():
            return False, f"« {nouveau} » existe déjà.", df_assets
        conn.execute("UPDATE referentiel SET value = ? WHERE kind = 'courtier' AND value = ?", (nouveau, ancien))
        conn.execute("UPDATE actifs SET courtier = ? WHERE courtier = ?", (nouveau, ancien))
        conn.commit()
    finally:
        conn.close()
    if not df_assets.empty:
        mask = df_assets["courtier"].astype(str).str.strip() == ancien
        df_assets = df_assets.copy()
        df_assets.loc[mask, "courtier"] = nouveau
        nb = int(mask.sum())
    else:
        nb = 0
    detail = f" ({nb} actif(s) mis à jour)" if nb > 0 else ""
    return True, f"Courtier renommé en « {nouveau} »{detail}.", df_assets


# ── Export ────────────────────────────────────────────────────────────────────

def download_historique_bytes() -> bytes:
    return load_historique().to_csv(index=False).encode("utf-8")


def download_positions_bytes() -> bytes:
    return load_positions().to_csv(index=False).encode("utf-8")