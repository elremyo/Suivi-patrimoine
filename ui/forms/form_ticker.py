"""
ui/forms/form_ticker.py
────────────────────────
Formulaire création / édition d'un actif à ticker (Actions & Fonds, Crypto).
La catégorie est fixée en amont par le popover.

Point d'entrée : render_form(df, mode, idx, row, invalidate_cache_fn, flash_fn, categorie)
"""
import streamlit as st
from services.asset_manager import create_auto_asset, edit_auto_asset
from ui.forms._shared import close_dialog, contrat_fields, resolve_contrat_id, ticker_picker, cancel_button


def render_form(df, mode, idx, row, invalidate_cache_fn, flash_fn, categorie: str = "Actions & Fonds"):
    if mode == "edit":
        categorie = row["categorie"]

    st.write(f"Categorie: {categorie}")

    initial_ticker   = row.get("ticker", "")             if mode == "edit" else ""
    initial_quantite = float(row.get("quantite") or 0.0) if mode == "edit" else 0.0
    initial_pru      = float(row.get("pru")      or 0.0) if mode == "edit" else 0.0

    contrat_id = contrat_fields(row if mode == "edit" else None)

    ticker_result = ticker_picker(initial_ticker=initial_ticker)
    if ticker_result is None:
        cancel_button()
        return df

    if mode == "create":
        col_quantite, col_pru = st.columns(2)
        with col_quantite:
            if categorie == "Crypto":
                step = 0.001
            else:
                step = 1.0
            quantite = st.number_input("Quantité", min_value=0.0, value=initial_quantite, step=step, format="%g", key="_form_quantite")
        with col_pru:
            pru = st.number_input("PRU (€)", min_value=0.0, value=initial_pru, step=1.0, format="%g", key="_form_pru", help="Prix de Revient Unitaire, prix d'achat hors frais.")
    else:
        quantite = float(row.get("quantite") or 0.0)
        pru      = float(row.get("pru")      or 0.0)
        st.caption(f"Position actuelle : {quantite:g} unités · PRU {pru:g} € — modifiable via :material/history:")

    c1, c2 = st.columns(2)
    if c1.button("Annuler", width="stretch", key="_form_cancel"):
        close_dialog()
        st.rerun()

    if c2.button("Sauvegarder", type="primary", width="stretch", key="_form_save"):
        final_contrat_id = resolve_contrat_id(contrat_id)
        if not final_contrat_id:
            st.warning("Le contrat est obligatoire.")
        else:
            effective_ticker = ticker_result["ticker"]
            if mode == "create":
                with st.spinner("Ajout en cours…"):
                    df, msg, msg_type = create_auto_asset(df, effective_ticker, quantite, pru, categorie, contrat_id=final_contrat_id)
            else:
                ticker_current   = row.get("ticker", "")
                quantite_current = float(row.get("quantite") or 0.0)
                with st.spinner("Synchronisation du prix…"):
                    df, msg, msg_type = edit_auto_asset(df, idx, row["id"], effective_ticker, ticker_current, quantite, quantite_current, pru, categorie, contrat_id=final_contrat_id)
            flash_fn(msg, msg_type)
            close_dialog()
            invalidate_cache_fn()
            st.rerun()

    return df