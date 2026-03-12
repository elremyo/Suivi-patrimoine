"""
db_emprunts.py
─────────────
Gestion des emprunts et calcul du capital restant dû.
"""

import uuid
import pandas as pd
from datetime import date
from .db import db_readonly, db_connection


def _compute_capital_restant_du(
    montant_emprunte: float,
    taux_annuel: float,
    mensualite: float,
    date_debut,
    duree_mois: int,
    as_of_date: date | None = None,
) -> float:
    """Calcule le capital restant dû à une date donnée."""
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
    """Charge tous les emprunts avec calcul du capital restant dû."""
    with db_readonly() as conn:
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


def create_emprunt(nom, montant_emprunte, taux_annuel, mensualite, duree_mois, date_debut, date_fin=None) -> str:
    """Crée un nouvel emprunt."""
    emprunt_id = str(uuid.uuid4())
    with db_connection() as conn:
        conn.execute(
            """INSERT INTO emprunts (id, nom, montant_emprunte, taux_annuel, mensualite, duree_mois, date_debut, date_fin)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (emprunt_id, nom.strip(), float(montant_emprunte), float(taux_annuel), float(mensualite), int(duree_mois),
             date_debut if isinstance(date_debut, str) else pd.Timestamp(date_debut).strftime("%Y-%m-%d"),
             date_fin if date_fin is None or (isinstance(date_fin, str) and not date_fin.strip()) else (date_fin if isinstance(date_fin, str) else pd.Timestamp(date_fin).strftime("%Y-%m-%d"))),
        )
    return emprunt_id


def update_emprunt(emprunt_id, nom, montant_emprunte, taux_annuel, mensualite, duree_mois, date_debut, date_fin=None) -> None:
    """Met à jour un emprunt existant."""
    with db_connection() as conn:
        conn.execute(
            """UPDATE emprunts SET nom = ?, montant_emprunte = ?, taux_annuel = ?, mensualite = ?, duree_mois = ?,
               date_debut = ?, date_fin = ?, updated_at = datetime('now') WHERE id = ?""",
            (nom.strip(), float(montant_emprunte), float(taux_annuel), float(mensualite), int(duree_mois),
             date_debut if isinstance(date_debut, str) else pd.Timestamp(date_debut).strftime("%Y-%m-%d"),
             date_fin if date_fin is None or (isinstance(date_fin, str) and not date_fin.strip()) else (date_fin if isinstance(date_fin, str) else pd.Timestamp(date_fin).strftime("%Y-%m-%d")),
             emprunt_id),
        )


def delete_emprunt(emprunt_id: str) -> None:
    """Supprime un emprunt."""
    with db_connection() as conn:
        conn.execute("DELETE FROM emprunts WHERE id = ?", (emprunt_id,))


def get_total_emprunts(as_of_date: date | None = None) -> float:
    """Calcule le total des capitaux restant dus."""
    df = load_emprunts(as_of_date=as_of_date)
    if df.empty:
        return 0.0
    return float(df["capital_restant_du"].fillna(0).sum())
