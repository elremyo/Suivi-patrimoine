"""
db_contrats.py
─────────────
Gestion des contrats (établissement + enveloppe).
"""

import sqlite3
import uuid
from .db import db_readonly, db_connection


def load_contrats():
    """Retourne tous les contrats avec colonnes : id, etablissement, enveloppe."""
    with db_readonly() as conn:
        import pandas as pd
        df = pd.read_sql_query(
            "SELECT id, etablissement, enveloppe FROM contrats ORDER BY etablissement, enveloppe",
            conn,
        )
        return df


def get_or_create_contrat(etablissement: str, enveloppe: str) -> str:
    """
    Retourne l'id du contrat correspondant à (etablissement, enveloppe).
    Le crée s'il n'existe pas encore.
    """
    etablissement = etablissement.strip()
    enveloppe = enveloppe.strip()
    with db_connection() as conn:
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
        return contrat_id


def add_contrat(etablissement: str, enveloppe: str) -> tuple[bool, str, str | None]:
    """
    Crée un nouveau contrat. Retourne (succès, message, contrat_id).
    Échoue si le couple (etablissement, enveloppe) existe déjà.
    """
    etablissement = etablissement.strip()
    enveloppe = enveloppe.strip()
    if not etablissement or not enveloppe:
        return False, "L'établissement et l'enveloppe sont obligatoires.", None
    try:
        with db_connection() as conn:
            contrat_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO contrats (id, etablissement, enveloppe) VALUES (?, ?, ?)",
                (contrat_id, etablissement, enveloppe),
            )
            return True, f"Contrat « {etablissement} — {enveloppe} » ajouté.", contrat_id
    except sqlite3.IntegrityError:
        return False, f"« {etablissement} — {enveloppe} » existe déjà.", None


def update_contrat(contrat_id: str, etablissement: str, enveloppe: str) -> tuple[bool, str]:
    """Met à jour un contrat existant."""
    etablissement = etablissement.strip()
    enveloppe = enveloppe.strip()
    if not etablissement or not enveloppe:
        return False, "L'établissement et l'enveloppe sont obligatoires."
    with db_connection() as conn:
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
        return True, f"Contrat mis à jour : « {etablissement} — {enveloppe} »."


def delete_contrat(contrat_id: str) -> tuple[bool, str]:
    """
    Supprime un contrat seulement s'il n'est utilisé par aucun actif.
    """
    with db_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM actifs WHERE contrat_id = ?", (contrat_id,)
        ).fetchone()[0]
        if count > 0:
            return False, f"Ce contrat est utilisé par {count} actif(s) — modifie-les d'abord."
        conn.execute("DELETE FROM contrats WHERE id = ?", (contrat_id,))
        return True, "Contrat supprimé."
