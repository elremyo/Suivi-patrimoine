"""
ui/forms/form_emprunt.py
─────────────────────────
Modales pour la création, l'édition et la suppression d'un emprunt.

Session state : _emprunt_dialog
    {"type": "create"}
    {"type": "edit",   "emprunt_id": "..."}
    {"type": "delete", "emprunt_id": "..."}

Points d'entrée publics :
    set_emprunt_dialog_create()
    set_emprunt_dialog_edit(emprunt_id)
    set_emprunt_dialog_delete(emprunt_id)
    render_emprunt_dialog(flash_fn)
"""
import streamlit as st
import pandas as pd
from datetime import date

from services.db_emprunts import load_emprunts, create_emprunt, update_emprunt, delete_emprunt


# ── Gestion de l'état ─────────────────────────────────────────────────────────

def set_emprunt_dialog_create():
    st.session_state["_emprunt_dialog"] = {"type": "create"}


def set_emprunt_dialog_edit(emprunt_id: str):
    st.session_state["_emprunt_dialog"] = {"type": "edit", "emprunt_id": emprunt_id}


def set_emprunt_dialog_delete(emprunt_id: str):
    st.session_state["_emprunt_dialog"] = {"type": "delete", "emprunt_id": emprunt_id}


def _close_dialog():
    st.session_state.pop("_emprunt_dialog", None)
    for key in list(st.session_state.keys()):
        if key.startswith("_emprunt_form_"):
            st.session_state.pop(key, None)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _date_to_str(d) -> str:
    if d is None or (isinstance(d, float) and pd.isna(d)):
        return ""
    if isinstance(d, str):
        return d[:10] if len(d) >= 10 else d
    return pd.Timestamp(d).strftime("%Y-%m-%d")


def _find_emprunt(emprunt_id: str) -> pd.Series:
    df = load_emprunts()
    row = df[df["id"] == emprunt_id]
    if row.empty:
        raise ValueError("Emprunt introuvable.")
    return row.iloc[0]


def _format_duree(duree_mois: int) -> str:
    ans = duree_mois // 12
    mois = duree_mois % 12
    if ans == 0:
        return f"{mois} mois"
    if mois == 0:
        return f"{ans} ans"
    return f"{ans} ans {mois} mois"


# ── Formulaire (champs communs create / edit) ─────────────────────────────────

def _form_fields(edit_row: pd.Series | None, flash_fn) -> bool:
    nom = st.text_input(
        "Nom de l'emprunt *",
        value=str(edit_row["nom"]) if edit_row is not None else "",
        placeholder="Ex. Prêt immobilier résidence principale",
        key="_emprunt_form_nom",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        montant = st.number_input(
            "Montant emprunté (€)",
            min_value=0.0,
            value=float(edit_row["montant_emprunte"]) if edit_row is not None else 0.0,
            step=1000.0,
            key="_emprunt_form_montant",
        )
    with c2:
        taux = st.number_input(
            "Taux annuel (%)",
            min_value=0.0,
            value=float(edit_row["taux_annuel"]) if edit_row is not None else 0.0,
            step=0.1,
            format="%.2f",
            key="_emprunt_form_taux",
        )
    with c3:
        mensualite = st.number_input(
            "Mensualité (€)",
            min_value=0.0,
            value=float(edit_row["mensualite"]) if edit_row is not None else 0.0,
            step=50.0,
            key="_emprunt_form_mensualite",
        )

    d1, d2, d3 = st.columns([0.7, 0.3, 1], vertical_alignment="bottom")
    with d1:
        duree_mois = st.number_input(
            "Durée (mois)",
            min_value=1,
            max_value=360,
            value=int(edit_row["duree_mois"]) if edit_row is not None else 240,
            step=12,
            key="_emprunt_form_duree",
        )
    with d2:
        st.caption(_format_duree(duree_mois))
    with d3:
        date_debut_val = _date_to_str(edit_row["date_debut"]) if edit_row is not None else date.today().isoformat()
        date_debut = st.date_input(
            "Date de début",
            value=date.fromisoformat(date_debut_val) if date_debut_val else date.today(),
            key="_emprunt_form_date_debut",
        )

    c1, c2 = st.columns(2)
    if c1.button("Annuler", use_container_width=True, key="_emprunt_form_cancel"):
        _close_dialog()
        st.rerun()

    if c2.button("Sauvegarder", type="primary", use_container_width=True, key="_emprunt_form_save"):
        if not nom.strip():
            flash_fn("Le nom de l'emprunt est obligatoire.", "error")
            return False
        date_debut_str = date_debut.isoformat() if hasattr(date_debut, "isoformat") else str(date_debut)
        try:
            if edit_row is None:
                create_emprunt(
                    nom=nom.strip(),
                    montant_emprunte=montant,
                    taux_annuel=taux,
                    mensualite=mensualite,
                    duree_mois=duree_mois,
                    date_debut=date_debut_str,
                )
                flash_fn("Emprunt ajouté.", "success")
            else:
                update_emprunt(
                    edit_row["id"],
                    nom=nom.strip(),
                    montant_emprunte=montant,
                    taux_annuel=taux,
                    mensualite=mensualite,
                    duree_mois=duree_mois,
                    date_debut=date_debut_str,
                )
                flash_fn("Emprunt modifié.", "success")
        except Exception as e:
            flash_fn(f"Erreur : {e}", "error")
            return False
        _close_dialog()
        st.rerun()
    return False


# ── Modales ───────────────────────────────────────────────────────────────────

@st.dialog("Ajouter un emprunt", dismissible=False, width="large")
def _dialog_create(flash_fn):
    st.markdown("### Nouvel emprunt")
    _form_fields(None, flash_fn)


@st.dialog("Modifier l'emprunt", dismissible=False, width="large")
def _dialog_edit(emprunt_id: str, flash_fn):
    try:
        row = _find_emprunt(emprunt_id)
    except ValueError as e:
        st.error(str(e))
        if st.button("Fermer"):
            _close_dialog()
            st.rerun()
        return
    st.markdown(f"### {row['nom']}")
    _form_fields(row, flash_fn)


@st.dialog("Supprimer l'emprunt", dismissible=False)
def _dialog_delete(emprunt_id: str, flash_fn):
    try:
        row = _find_emprunt(emprunt_id)
    except ValueError as e:
        st.error(str(e))
        if st.button("Fermer"):
            _close_dialog()
            st.rerun()
        return
    st.warning(f"Supprimer **{row['nom']}** ? Les biens immobiliers liés ne seront plus associés à cet emprunt.")
    c1, c2 = st.columns(2)
    if c1.button("Annuler", use_container_width=True, key="_emprunt_delete_cancel"):
        _close_dialog()
        st.rerun()
    if c2.button("Confirmer", type="primary", use_container_width=True, key="_emprunt_delete_confirm"):
        delete_emprunt(emprunt_id)
        flash_fn("Emprunt supprimé.", "success")
        _close_dialog()
        st.rerun()


# ── Point d'entrée public ─────────────────────────────────────────────────────

def render_emprunt_dialog(flash_fn):
    dialog = st.session_state.get("_emprunt_dialog")
    if not dialog:
        return
    dtype = dialog["type"]
    if dtype == "create":
        _dialog_create(flash_fn)
    elif dtype == "edit":
        _dialog_edit(dialog["emprunt_id"], flash_fn)
    elif dtype == "delete":
        _dialog_delete(dialog["emprunt_id"], flash_fn)