"""
ui/forms/form_immo.py
──────────────────────
Formulaire création / édition d'un bien immobilier.
Catégorie fixée : "Immobilier".
Pas de contrat (l'immo n'est pas dans une enveloppe fiscale).

Point d'entrée : render_form(df, mode, idx, row, invalidate_cache_fn, flash_fn)
"""
import streamlit as st
import pandas as pd
from services.asset_manager import create_manual_asset, edit_manual_asset
from services.db_emprunts import load_emprunts
from ui.forms._shared import close_dialog
from constants import TYPE_BIEN_OPTIONS

CATEGORIE = "Immobilier"


def render_form(df, mode, idx, row, invalidate_cache_fn, flash_fn, categorie=None):
    initial_nom     = row["nom"]            if mode == "edit" else ""
    initial_montant = float(row["montant"]) if mode == "edit" else 0.0

    col_nom, col_montant = st.columns(2)
    with col_nom:
        nom = st.text_input("Nom *", value=initial_nom, key="_form_nom")
    with col_montant:
        montant = st.number_input("Valeur actuelle (€)", min_value=0.0, value=initial_montant, step=1000.0, key="_form_montant")

    st.markdown("**Détail immobilier**")

    type_bien_val = str(row.get("type_bien", "") or "autre").strip().lower() if mode == "edit" else "autre"
    if type_bien_val not in TYPE_BIEN_OPTIONS:
        type_bien_val = "autre"
    type_bien = st.selectbox(
        "Type de bien",
        options=TYPE_BIEN_OPTIONS,
        index=TYPE_BIEN_OPTIONS.index(type_bien_val),
        key="_form_type_bien",
    )
    usage_options = {"locatif": "Locatif", "residence_principale": "Résidence principale"}
    usage_val = str(row.get("usage") or "locatif") if mode == "edit" else "locatif"
    if usage_val not in usage_options:
        usage_val = "locatif"
    usage = st.radio(
        "Usage du bien",
        options=list(usage_options.keys()),
        format_func=lambda x: usage_options[x],
        index=list(usage_options.keys()).index(usage_val),
        horizontal=True,
        key="_form_usage",
    )
    prix_achat = st.number_input(
        "Prix d'achat (€)",
        min_value=0.0,
        value=float(row.get("prix_achat") or row.get("montant") or 0.0) if mode == "edit" else montant,
        step=1000.0,
        key="_form_prix_achat",
    )
    adresse = st.text_input(
        "Adresse",
        value=str(row.get("adresse") or "").strip() if mode == "edit" else "",
        placeholder="Optionnel",
        key="_form_adresse",
    )
    superficie = st.number_input(
        "Superficie (m²)",
        min_value=0.0,
        value=float(row.get("superficie_m2") or 0.0) if mode == "edit" else 0.0,
        step=5.0,
        key="_form_superficie",
    )

    st.markdown("**Coût d'acquisition**")
    col_notaire, col_travaux = st.columns(2)
    with col_notaire:
        frais_notaire = st.number_input(
            "Frais de notaire (€)",
            min_value=0.0,
            value=float(row.get("frais_notaire") or 0.0) if mode == "edit" else 0.0,
            step=500.0,
            key="_form_frais_notaire",
        )
    with col_travaux:
        montant_travaux = st.number_input(
            "Travaux (€)",
            min_value=0.0,
            value=float(row.get("montant_travaux") or 0.0) if mode == "edit" else 0.0,
            step=500.0,
            key="_form_montant_travaux",
        )
    cout_reel = prix_achat + frais_notaire + montant_travaux
    if cout_reel > prix_achat:
        st.caption(f":material/calculate: Coût réel d'acquisition : **{cout_reel:,.0f} €**")


    # ── Emprunt lié ──────────────────────────────────────────────────────────
    df_emprunts = load_emprunts()
    emprunt_options = ["Aucun"] + [r["nom"] for _, r in df_emprunts.iterrows()]

    current_emprunt_id = None
    if mode == "edit" and row is not None:
        current_emprunt_id = row.get("emprunt_id", None)
        current_emprunt_id = None if pd.isna(current_emprunt_id) or current_emprunt_id == "" else str(current_emprunt_id)

    if current_emprunt_id and not df_emprunts.empty:
        match = df_emprunts[df_emprunts["id"] == current_emprunt_id]
        default_idx = list(df_emprunts["id"]).index(current_emprunt_id) + 1 if not match.empty else 0
    else:
        default_idx = 0

    emprunt_choice = st.selectbox(
        "Emprunt lié",
        options=emprunt_options,
        index=min(default_idx, len(emprunt_options) - 1),
        key="_form_emprunt",
    )
    emprunt_id = None if emprunt_choice == "Aucun" else df_emprunts.iloc[emprunt_options.index(emprunt_choice) - 1]["id"]

    immo_params = {
        "prix_achat": prix_achat,
        "type_bien": type_bien,
        "adresse": adresse,
        "superficie_m2": superficie,
        "emprunt_id": emprunt_id,
        "frais_notaire": frais_notaire,
        "montant_travaux": montant_travaux,
        "usage": usage,
    }

    c1, c2 = st.columns(2)
    if c1.button("Annuler", use_container_width=True, key="_form_cancel"):
        close_dialog()
        st.rerun()

    if c2.button("Sauvegarder", type="primary", use_container_width=True, key="_form_save"):
        if not nom.strip():
            st.warning("Le nom est obligatoire.")
        else:
            if mode == "create":
                df, msg, msg_type = create_manual_asset(df, nom.strip(), CATEGORIE, montant, immo_params=immo_params)
            else:
                df, msg, msg_type = edit_manual_asset(df, idx, row["id"], nom.strip(), CATEGORIE, montant, immo_params=immo_params)
            flash_fn(msg, msg_type)
            close_dialog()
            invalidate_cache_fn()
            st.rerun()

    return df