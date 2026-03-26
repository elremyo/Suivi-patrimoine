"""
ui/asset_form.py
─────────────────
Coordinateur des modales actifs.
Ce fichier gère uniquement :
  - l'état du session_state (_dialog)
  - les décorateurs @st.dialog (obligatoirement ici, Streamlit l'exige)
  - le dispatch vers les formulaires dédiés dans ui/forms/

Points d'entrée publics :
    set_dialog_create(categorie)
    set_dialog_edit(asset_id)
    set_dialog_delete(asset_id)
    set_dialog_update(asset_id)
    render_active_dialog(df, invalidate_cache_fn, flash_fn)
"""
import streamlit as st
import pandas as pd
from datetime import date

from services.asset_manager import remove_asset, update_at_date
from constants import CATEGORIES_AUTO

from ui.forms._shared import close_dialog
import ui.forms.form_ticker      as _f_ticker
import ui.forms.form_livret      as _f_livret
import ui.forms.form_immo        as _f_immo
import ui.forms.form_fonds_euros as _f_fonds_euros


# ── Mapping catégorie → module formulaire ─────────────────────────────────────

_FORM_MAP = {
    "Actions & Fonds": _f_ticker,
    "Crypto":          _f_ticker,
    "Livrets":         _f_livret,
    "Immobilier":      _f_immo,
    "Fonds euros":     _f_fonds_euros,
}


# ── Gestion de l'état ─────────────────────────────────────────────────────────

def set_dialog_create(categorie: str):
    st.session_state["_dialog"] = {"type": "create", "categorie": categorie}

def set_dialog_edit(asset_id: str):
    st.session_state["_dialog"] = {"type": "edit", "asset_id": asset_id}

def set_dialog_delete(asset_id: str):
    st.session_state["_dialog"] = {"type": "delete", "asset_id": asset_id}

def set_dialog_update(asset_id: str):
    st.session_state["_dialog"] = {"type": "update", "asset_id": asset_id}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_row_by_id(df: pd.DataFrame, asset_id: str):
    matches = df[df["id"] == asset_id]
    if matches.empty:
        raise ValueError(f"Actif introuvable (id={asset_id}).")
    return matches.index[0], matches.iloc[0]


# ── Modales (@st.dialog doit rester dans ce fichier) ─────────────────────────

@st.dialog("Ajouter un actif", dismissible=False, width="large")
def _dialog_create(df, invalidate_cache_fn, flash_fn, categorie: str):
    st.markdown(f"## {categorie}")
    form_module = _FORM_MAP.get(categorie)
    if form_module is None:
        st.error(f"Catégorie inconnue : {categorie}")
        return
    form_module.render_form(df, "create", None, None, invalidate_cache_fn, flash_fn, categorie)


@st.dialog("Modifier un actif", dismissible=False, width="large")
def _dialog_edit(df, asset_id, invalidate_cache_fn, flash_fn):
    try:
        idx, row = _find_row_by_id(df, asset_id)
    except ValueError as e:
        st.error(str(e))
        if st.button("Fermer"):
            close_dialog()
            st.rerun()
        return

    st.markdown(f"### Modifier — {row['nom']}")
    form_module = _FORM_MAP.get(row["categorie"])
    if form_module is None:
        st.error(f"Catégorie inconnue : {row['categorie']}")
        return
    form_module.render_form(df, "edit", idx, row, invalidate_cache_fn, flash_fn)


@st.dialog("Supprimer un actif", dismissible=False)
def _dialog_delete(df, asset_id, invalidate_cache_fn, flash_fn):
    try:
        idx, row = _find_row_by_id(df, asset_id)
    except ValueError as e:
        st.error(str(e))
        if st.button("Fermer"):
            close_dialog()
            st.rerun()
        return

    st.warning(f"Supprimer **{row['nom']}** ? Cette action est irréversible.")
    c1, c2 = st.columns(2)
    if c1.button("Annuler", width="stretch", key="_delete_cancel"):
        close_dialog()
        st.rerun()
    if c2.button("Confirmer", type="primary", width="stretch", key="_delete_confirm"):
        df, msg, msg_type = remove_asset(df, idx, row["id"])
        flash_fn(msg, msg_type)
        close_dialog()
        invalidate_cache_fn()
        st.rerun()


@st.dialog("Mettre à jour un montant", dismissible=False)
def _dialog_update(df, asset_id, invalidate_cache_fn, flash_fn):
    try:
        idx, row = _find_row_by_id(df, asset_id)
    except ValueError as e:
        st.error(str(e))
        if st.button("Fermer"):
            close_dialog()
            st.rerun()
        return

    is_auto = row["categorie"] in CATEGORIES_AUTO
    ticker  = row.get("ticker", "")
    st.caption(row["nom"] + (f" · {ticker}" if ticker else ""))

    op_date = st.date_input(
        "Date de l'opération",
        value=date.today(),
        key="_upd_date",
        help="Date réelle de l'opération, si différente d'aujourd'hui.",
    )

    if is_auto:
        quantite = st.number_input(
            "Nouvelle quantité totale détenue",
            min_value=0.0,
            value=float(row.get("quantite") or 0.0),
            step=1.0,
            format="%g",
            key="_upd_quantite",
        )
        pru = st.number_input(
            "Nouveau PRU (€)",
            min_value=0.0,
            value=float(row.get("pru") or 0.0),
            step=1.0,
            format="%g",
            key="_upd_pru",
            help="Prix de Revient Unitaire",
        )
    else:
        montant = st.number_input(
            "Montant total (€)",
            min_value=0.0,
            value=float(row.get("montant") or 0.0),
            step=100.0,
            key="_upd_montant",
        )

    c1, c2 = st.columns(2)
    if c1.button("Annuler", width="stretch", key="_upd_cancel"):
        close_dialog()
        st.rerun()

    if c2.button("Enregistrer", type="primary", width="stretch", key="_upd_save"):
        if is_auto:
            with st.spinner("Enregistrement…"):
                df, msg, msg_type = update_at_date(df, asset_id, row["categorie"], op_date=op_date, quantite=quantite, pru=pru)
        else:
            df, msg, msg_type = update_at_date(df, asset_id, row["categorie"], op_date=op_date, montant=montant)
        flash_fn(msg, msg_type)
        close_dialog()
        invalidate_cache_fn()
        st.rerun()


# ── Point d'entrée public ─────────────────────────────────────────────────────

def render_active_dialog(df: pd.DataFrame, invalidate_cache_fn, flash_fn):
    dialog = st.session_state.get("_dialog")
    if not dialog:
        return

    dtype = dialog["type"]
    if dtype == "create":
        _dialog_create(df, invalidate_cache_fn, flash_fn, categorie=dialog.get("categorie", "Actions & Fonds"))
    elif dtype == "edit":
        _dialog_edit(df, dialog["asset_id"], invalidate_cache_fn, flash_fn)
    elif dtype == "delete":
        _dialog_delete(df, dialog["asset_id"], invalidate_cache_fn, flash_fn)
    elif dtype == "update":
        _dialog_update(df, dialog["asset_id"], invalidate_cache_fn, flash_fn)