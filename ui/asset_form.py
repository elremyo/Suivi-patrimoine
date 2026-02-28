"""
ui/asset_form.py
─────────────────
Modale unique pour la création, l'édition et la suppression d'un actif.

Gestion du session state :
- Une seule clé `_dialog` centralise ce qui doit être affiché :
    {"type": "create"}
    {"type": "edit",   "asset_id": "..."}
    {"type": "delete", "asset_id": "..."}
- Toute ouverture écrase la précédente → impossible d'avoir deux modales.
- Toute fermeture (save/cancel) supprime `_dialog` avant st.rerun().
- La croix Streamlit ne peut pas être interceptée : si `_dialog` est encore
  présent après un clic X, la modale se rouvre. L'utilisateur doit utiliser
  Annuler pour fermer proprement. C'est une limitation connue de st.dialog.

Points d'entrée publics :
    set_dialog_create()
    set_dialog_edit(asset_id)
    set_dialog_delete(asset_id)
    render_active_dialog(df, invalidate_cache_fn, flash_fn)
"""

import streamlit as st
import pandas as pd
from services.asset_manager import (
    create_auto_asset, create_manual_asset,
    edit_auto_asset, edit_manual_asset,
    remove_asset,
)
from services.pricer import validate_ticker, lookup_ticker
from constants import CATEGORIES_ASSETS, CATEGORIES_AUTO


# ── Gestion de l'état des modales ─────────────────────────────────────────────

def set_dialog_create():
    st.session_state["_dialog"] = {"type": "create"}

def set_dialog_edit(asset_id: str):
    st.session_state["_dialog"] = {"type": "edit", "asset_id": asset_id}

def set_dialog_delete(asset_id: str):
    st.session_state["_dialog"] = {"type": "delete", "asset_id": asset_id}

def _close_dialog():
    """Ferme la modale et nettoie tout l'état du formulaire."""
    st.session_state.pop("_dialog", None)
    # Nettoie les clés internes du formulaire
    for key in list(st.session_state.keys()):
        if key.startswith("_form_"):
            st.session_state.pop(key, None)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_row_by_id(df: pd.DataFrame, asset_id: str):
    matches = df[df["id"] == asset_id]
    if matches.empty:
        raise ValueError(f"Actif introuvable (id={asset_id}).")
    return matches.index[0], matches.iloc[0]


# ── Ticker picker ─────────────────────────────────────────────────────────────

def _ticker_picker(initial_ticker: str = "") -> dict | None:
    """
    Composant de sélection et validation d'un ticker.

    - Ticker inchangé en mode édition → retour immédiat sans fiche ni vérification.
    - Ticker nouveau ou création → bouton "Vérifier" obligatoire + fiche affichée.

    Retourne un dict {ticker, name, price, currency} ou None si pas encore validé.
    """
    ticker_input = st.text_input(
        "Ticker *",
        value=initial_ticker,
        placeholder="ex. AAPL, BTC-USD, CW8.PA",
        key="_form_ticker_input",
    ).strip().upper()

    # Détecte un changement de ticker et efface l'aperçu
    if st.session_state.get("_form_ticker_last") != ticker_input:
        st.session_state.pop("_form_ticker_preview", None)
        st.session_state["_form_ticker_last"] = ticker_input

    # Édition : ticker inchangé → on fait confiance aux données existantes
    if ticker_input == initial_ticker and initial_ticker != "":
        return {"ticker": ticker_input, "prefilled": True}

    # Bouton de vérification
    if st.button(
        "Vérifier le ticker",
        use_container_width=True,
        key="_form_verify_btn",
    ):
        valid, err = validate_ticker(ticker_input)
        if not valid:
            st.error(err)
        else:
            with st.spinner("Recherche en cours…"):
                result = lookup_ticker(ticker_input)
            if result:
                st.session_state["_form_ticker_preview"] = result
            else:
                st.error(f"Ticker « {ticker_input} » introuvable sur yfinance.")

    # Fiche de l'actif trouvé
    if "_form_ticker_preview" in st.session_state:
        preview = st.session_state["_form_ticker_preview"]
        with st.container(border=True):
            st.markdown(f"**{preview['name']}**")
            price_str = f"{preview['price']:,.4f} {preview['currency']}".strip()
            st.caption(f"{preview['ticker']} · {price_str}")
        return preview

    return None


# ── Formulaire actif automatique ──────────────────────────────────────────────

def _form_auto(df, mode, idx, row, invalidate_cache_fn, flash_fn):
    initial_ticker   = row.get("ticker", "")    if mode == "edit" else ""
    initial_quantite = float(row.get("quantite") or 0.0) if mode == "edit" else 0.0
    initial_pru      = float(row.get("pru")      or 0.0) if mode == "edit" else 0.0
    auto_categories  = [c for c in CATEGORIES_ASSETS if c in CATEGORIES_AUTO]
    initial_categorie = row["categorie"] if mode == "edit" and row["categorie"] in auto_categories else auto_categories[0]

    ticker_result = _ticker_picker(initial_ticker=initial_ticker)

    if ticker_result is None:
        st.info("Vérifiez le ticker pour continuer.")
        _cancel_button()
        return df

    quantite = st.number_input("Quantité", min_value=0.0, value=initial_quantite, step=1.0, format="%g", key="_form_quantite")
    pru      = st.number_input("PRU (€)",  min_value=0.0, value=initial_pru,      step=1.0, format="%g", key="_form_pru")
    categorie = st.selectbox(
        "Catégorie", options=auto_categories,
        index=auto_categories.index(initial_categorie),
        key="_form_categorie",
    )

    c1, c2 = st.columns(2)
    if c1.button("Annuler", use_container_width=True, key="_form_cancel"):
        _close_dialog()
        st.rerun()

    if c2.button("Sauvegarder", type="primary", use_container_width=True, key="_form_save"):
        effective_ticker = ticker_result["ticker"]
        if mode == "create":
            with st.spinner("Ajout en cours…"):
                df, msg, msg_type = create_auto_asset(df, effective_ticker, quantite, pru, categorie)
        else:
            ticker_current   = row.get("ticker", "")
            quantite_current = float(row.get("quantite") or 0.0)
            with st.spinner("Synchronisation du prix…"):
                df, msg, msg_type = edit_auto_asset(
                    df, idx, row["id"],
                    effective_ticker, ticker_current,
                    quantite, quantite_current,
                    pru, categorie,
                )
        flash_fn(msg, msg_type)
        _close_dialog()
        invalidate_cache_fn()
        st.rerun()

    return df


# ── Formulaire actif manuel ───────────────────────────────────────────────────

def _form_manual(df, mode, idx, row, invalidate_cache_fn, flash_fn):
    manual_categories = [c for c in CATEGORIES_ASSETS if c not in CATEGORIES_AUTO]
    initial_nom       = row["nom"]            if mode == "edit" else ""
    initial_montant   = float(row["montant"]) if mode == "edit" else 0.0
    initial_categorie = row["categorie"] if mode == "edit" and row["categorie"] in manual_categories else manual_categories[0]

    nom      = st.text_input("Nom *", value=initial_nom, key="_form_nom")
    montant  = st.number_input("Montant (€)", min_value=0.0, value=initial_montant, step=100.0, key="_form_montant")
    categorie = st.selectbox(
        "Catégorie", options=manual_categories,
        index=manual_categories.index(initial_categorie),
        key="_form_categorie",
    )

    c1, c2 = st.columns(2)
    if c1.button("Annuler", use_container_width=True, key="_form_cancel"):
        _close_dialog()
        st.rerun()

    if c2.button("Sauvegarder", type="primary", use_container_width=True, key="_form_save"):
        if not nom:
            st.warning("Le nom est obligatoire.")
        else:
            if mode == "create":
                df, msg, msg_type = create_manual_asset(df, nom, categorie, montant)
            else:
                df, msg, msg_type = edit_manual_asset(df, idx, row["id"], nom, categorie, montant)
            flash_fn(msg, msg_type)
            _close_dialog()
            invalidate_cache_fn()
            st.rerun()

    if c1.button("Annuler", use_container_width=True, key="_form_cancel"):
        _close_dialog()
        st.rerun()

    return df


def _cancel_button():
    """Bouton Annuler standalone (quand le formulaire n'est pas encore complet)."""
    if st.button("Annuler", use_container_width=True, key="_form_cancel_early"):
        _close_dialog()
        st.rerun()


# ── Modales Streamlit ─────────────────────────────────────────────────────────

@st.dialog("Actif",dismissible=False)
def _dialog_create(df, invalidate_cache_fn, flash_fn):
    st.markdown("### Ajouter un actif")
    is_auto = st.toggle("Actif financier (ticker)", value=True, key="_form_is_auto")
    if is_auto:
        _form_auto(df, "create", None, None, invalidate_cache_fn, flash_fn)
    else:
        _form_manual(df, "create", None, None, invalidate_cache_fn, flash_fn)


@st.dialog("Actif",dismissible=False)
def _dialog_edit(df, asset_id, invalidate_cache_fn, flash_fn):
    try:
        idx, row = _find_row_by_id(df, asset_id)
    except ValueError as e:
        st.error(str(e))
        if st.button("Fermer"):
            _close_dialog()
            st.rerun()
        return

    st.markdown(f"### Modifier — {row['nom']}")
    if row["categorie"] in CATEGORIES_AUTO:
        _form_auto(df, "edit", idx, row, invalidate_cache_fn, flash_fn)
    else:
        _form_manual(df, "edit", idx, row, invalidate_cache_fn, flash_fn)


@st.dialog("Supprimer un actif",dismissible=False)
def _dialog_delete(df, asset_id, invalidate_cache_fn, flash_fn):
    try:
        idx, row = _find_row_by_id(df, asset_id)
    except ValueError as e:
        st.error(str(e))
        if st.button("Fermer"):
            _close_dialog()
            st.rerun()
        return

    st.warning(f"Supprimer **{row['nom']}** ? Cette action est irréversible.")
    c1, c2 = st.columns(2)
    if c1.button("Annuler", use_container_width=True, key="_delete_cancel"):
        _close_dialog()
        st.rerun()
    if c2.button("Confirmer", type="primary", use_container_width=True, key="_delete_confirm"):
        df, msg, msg_type = remove_asset(df, idx, row["id"])
        flash_fn(msg, msg_type)
        _close_dialog()
        invalidate_cache_fn()
        st.rerun()



# ── Point d'entrée public ─────────────────────────────────────────────────────

def render_active_dialog(df: pd.DataFrame, invalidate_cache_fn, flash_fn):
    """
    À appeler une seule fois par script run (dans app.py).
    Ouvre la modale correspondant à `_dialog` en session state, si présente.
    """
    dialog = st.session_state.get("_dialog")
    if not dialog:
        return

    dtype = dialog["type"]
    if dtype == "create":
        _dialog_create(df, invalidate_cache_fn, flash_fn)
    elif dtype == "edit":
        _dialog_edit(df, dialog["asset_id"], invalidate_cache_fn, flash_fn)
    elif dtype == "delete":
        _dialog_delete(df, dialog["asset_id"], invalidate_cache_fn, flash_fn)