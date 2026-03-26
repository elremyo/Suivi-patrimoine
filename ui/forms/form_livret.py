"""
ui/forms/form_livret.py
────────────────────────
Formulaire création / édition d'un livret.
Catégorie fixée : "Livrets".

Point d'entrée : render_form(df, mode, idx, row, invalidate_cache_fn, flash_fn)
"""
import streamlit as st
from services.asset_manager import create_manual_asset, edit_manual_asset
from ui.forms._shared import close_dialog, contrat_fields, resolve_contrat_id

CATEGORIE = "Livrets"


def render_form(df, mode, idx, row, invalidate_cache_fn, flash_fn, categorie=None):
    initial_nom     = row["nom"]            if mode == "edit" else ""
    initial_montant = float(row["montant"]) if mode == "edit" else 0.0
    categorie       = row["categorie"]      if mode == "edit" else CATEGORIE

    contrat_id = contrat_fields(row if mode == "edit" else None)

    col_nom, col_montant = st.columns(2)
    with col_nom:
        nom = st.text_input("Nom *", value=initial_nom, key="_form_nom")
    with col_montant:
        montant = st.number_input("Montant (€)", min_value=0.0, value=initial_montant, step=100.0, key="_form_montant")

    c1, c2 = st.columns(2)
    if c1.button("Annuler", width="stretch", key="_form_cancel"):
        close_dialog()
        st.rerun()

    if c2.button("Sauvegarder", type="primary", width="stretch", key="_form_save"):
        final_contrat_id = resolve_contrat_id(contrat_id)
        if not nom.strip():
            st.warning("Le nom est obligatoire.")
        elif not final_contrat_id:
            st.warning("Le contrat est obligatoire.")
        else:
            if mode == "create":
                df, msg, msg_type = create_manual_asset(df, nom.strip(), categorie, montant, contrat_id=final_contrat_id)
            else:
                df, msg, msg_type = edit_manual_asset(df, idx, row["id"], nom.strip(), categorie, montant, contrat_id=final_contrat_id)
            flash_fn(msg, msg_type)
            close_dialog()
            invalidate_cache_fn()
            st.rerun()

    return df