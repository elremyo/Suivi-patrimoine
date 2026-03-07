"""
ui/asset_form.py
─────────────────
Modale unique pour la création, l'édition et la suppression d'un actif.
+ Modale légère "Mettre à jour" pour enregistrer un état à une date donnée.

Gestion du session state :
- Une seule clé `_dialog` centralise ce qui doit être affiché :
    {"type": "create"}
    {"type": "edit",   "asset_id": "..."}
    {"type": "delete", "asset_id": "..."}
    {"type": "update", "asset_id": "..."}
- Toute ouverture écrase la précédente → impossible d'avoir deux modales.
- Toute fermeture (save/cancel) supprime `_dialog` avant st.rerun().

Points d'entrée publics :
    set_dialog_create()
    set_dialog_edit(asset_id)
    set_dialog_delete(asset_id)
    set_dialog_update(asset_id)
    render_active_dialog(df, invalidate_cache_fn, flash_fn)
"""

import streamlit as st
import pandas as pd
from services.asset_manager import (
    create_auto_asset, create_manual_asset,
    edit_auto_asset, edit_manual_asset,
    remove_asset, update_at_date,
)
from services.pricer import validate_ticker, lookup_ticker
from services.referentiel import get_courtiers, add_courtier
from constants import CATEGORIES_ASSETS, CATEGORIES_AUTO, ENVELOPPES, TYPE_BIEN_OPTIONS
from services.db import load_emprunts


# ── Gestion de l'état des modales ─────────────────────────────────────────────

def set_dialog_create():
    st.session_state["_dialog"] = {"type": "create"}

def set_dialog_edit(asset_id: str):
    st.session_state["_dialog"] = {"type": "edit", "asset_id": asset_id}

def set_dialog_delete(asset_id: str):
    st.session_state["_dialog"] = {"type": "delete", "asset_id": asset_id}

def set_dialog_update(asset_id: str):
    st.session_state["_dialog"] = {"type": "update", "asset_id": asset_id}

def _close_dialog():
    """Ferme la modale et nettoie tout l'état du formulaire."""
    st.session_state.pop("_dialog", None)
    for key in list(st.session_state.keys()):
        if key.startswith("_form_") or key.startswith("_upd_"):
            st.session_state.pop(key, None)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_row_by_id(df: pd.DataFrame, asset_id: str):
    matches = df[df["id"] == asset_id]
    if matches.empty:
        raise ValueError(f"Actif introuvable (id={asset_id}).")
    return matches.index[0], matches.iloc[0]


def _courtier_enveloppe_fields(row=None, show_enveloppe=True):
    """
    Affiche les champs Courtier et Enveloppe sous forme de listes déroulantes
    alimentées par le référentiel. Si l'utilisateur choisit "+ Nouveau...",
    un champ texte apparaît pour saisir une nouvelle valeur.
    La nouvelle valeur est enregistrée dans le référentiel à la sauvegarde.
    """
    initial_courtier  = str(row.get("courtier",  "") or "").strip() if row is not None else ""
    initial_enveloppe = str(row.get("enveloppe", "") or "").strip() if row is not None else ""

    NOUVEAU_COURTIER  = "+ Nouveau courtier"

    # ── Courtier ──────────────────────────────────────────────────────────────
    courtiers = get_courtiers()

    # Si la valeur actuelle n'est pas encore dans le référentiel, on l'affiche quand même
    courtier_options = courtiers[:]
    if initial_courtier and initial_courtier not in courtier_options:
        courtier_options.insert(0, initial_courtier)
    courtier_options.append(NOUVEAU_COURTIER)

    default_idx = courtier_options.index(initial_courtier) if initial_courtier in courtier_options else 0

    courtier_selection = st.selectbox(
        "Courtier / Banque *",
        options=courtier_options,
        index=default_idx,
        key="_form_courtier_select",
    )

    if courtier_selection == NOUVEAU_COURTIER:
        courtier = st.text_input(
            "Nom du nouveau courtier",
            placeholder="ex. Boursorama, Binance, Crédit Agricole",
            key="_form_courtier_new",
        ).strip()
    else:
        courtier = courtier_selection

    # ── Enveloppe ─────────────────────────────────────────────────────────────
    enveloppe = ""
    if show_enveloppe:
        enveloppe_options = sorted(ENVELOPPES)
        default_idx_env = enveloppe_options.index(initial_enveloppe) if initial_enveloppe in enveloppe_options else 0
        enveloppe = st.selectbox(
            "Enveloppe *",
            options=enveloppe_options,
            index=default_idx_env,
            key="_form_enveloppe_select",
        )

    return courtier, enveloppe


def _save_referentiel(courtier: str):
    """Enregistre le courtier dans le référentiel si c'est une nouvelle valeur."""
    if courtier:
        add_courtier(courtier)   # idempotent : ignore si déjà présent


# ── Ticker picker ─────────────────────────────────────────────────────────────

def _ticker_picker(initial_ticker: str = "") -> dict | None:
    help_ticker=""":small[Le ticker est affiché entre parenthèses sur https://finance.yahoo.com/markets/]"""

    ticker_input = st.text_input(
        "Ticker *",
        value=initial_ticker,
        placeholder="ex. AAPL, BTC-USD, CW8.PA",
        key="_form_ticker_input",
        help=help_ticker
    ).strip().upper()

    if st.session_state.get("_form_ticker_last") != ticker_input:
        st.session_state.pop("_form_ticker_preview", None)
        st.session_state["_form_ticker_last"] = ticker_input

    if ticker_input == initial_ticker and initial_ticker != "":
        return {"ticker": ticker_input, "prefilled": True}

    if st.button(
        "Vérifier le ticker",
        use_container_width=True,
        key="_form_verify_btn",
        icon=":material/search_check_2:",
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
    initial_ticker    = row.get("ticker", "")    if mode == "edit" else ""
    initial_quantite  = float(row.get("quantite") or 0.0) if mode == "edit" else 0.0
    initial_pru       = float(row.get("pru")      or 0.0) if mode == "edit" else 0.0
    auto_categories   = [c for c in CATEGORIES_ASSETS if c in CATEGORIES_AUTO]
    initial_categorie = row["categorie"] if mode == "edit" and row["categorie"] in auto_categories else auto_categories[0]

    ticker_result = _ticker_picker(initial_ticker=initial_ticker)

    if ticker_result is None:
        st.info("Vérifie le ticker pour continuer.")
        _cancel_button()
        return df

    if mode == "create":
        quantite = st.number_input("Quantité", min_value=0.0, value=initial_quantite, step=1.0, format="%g", key="_form_quantite")
        pru      = st.number_input("PRU (€)",  min_value=0.0, value=initial_pru,      step=1.0, format="%g", key="_form_pru", help="Prix de Revient Unitaire, Prix d'achat (hors frais).")
    else:
        quantite = float(row.get("quantite") or 0.0)
        pru      = float(row.get("pru")      or 0.0)
        st.caption(f"Position actuelle : {quantite:g} unités · PRU {pru:g} € — modifiable via 🕐")

    categorie = st.selectbox(
        "Catégorie", options=auto_categories,
        index=auto_categories.index(initial_categorie),
        key="_form_categorie",
    )

    courtier, enveloppe = _courtier_enveloppe_fields(row if mode == "edit" else None)

    c1, c2 = st.columns(2)
    if c1.button("Annuler", use_container_width=True, key="_form_cancel"):
        _close_dialog()
        st.rerun()

    if c2.button("Sauvegarder", type="primary", use_container_width=True, key="_form_save"):
        if not courtier:
            st.warning("Le courtier / la banque est obligatoire.")
        else:
            _save_referentiel(courtier)
            effective_ticker = ticker_result["ticker"]
            if mode == "create":
                with st.spinner("Ajout en cours…"):
                    df, msg, msg_type = create_auto_asset(
                        df, effective_ticker, quantite, pru, categorie,
                        courtier=courtier, enveloppe=enveloppe,
                    )
            else:
                ticker_current   = row.get("ticker", "")
                quantite_current = float(row.get("quantite") or 0.0)
                with st.spinner("Synchronisation du prix…"):
                    df, msg, msg_type = edit_auto_asset(
                        df, idx, row["id"],
                        effective_ticker, ticker_current,
                        quantite, quantite_current,
                        pru, categorie,
                        courtier=courtier, enveloppe=enveloppe,
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

    courtier, enveloppe = _courtier_enveloppe_fields(
        row if mode == "edit" else None,
        show_enveloppe=(categorie != "Immobilier"),
    )

    immo_params = None
    if categorie == "Immobilier":
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
        df_emprunts = load_emprunts()
        emprunt_options = ["Aucun"] + [f"{r['nom']}" for _, r in df_emprunts.iterrows()]
        if mode == "edit" and row is not None:
            current_emprunt_id = row.get("emprunt_id")
            current_emprunt_id = None if pd.isna(current_emprunt_id) or current_emprunt_id == "" else str(current_emprunt_id)
        else:
            current_emprunt_id = None
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
            "adresse": adresse.strip() or None,
            "superficie_m2": superficie if superficie > 0 else None,
            "emprunt_id": emprunt_id,
        }

    c1, c2 = st.columns(2)
    if c1.button("Annuler", use_container_width=True, key="_form_cancel"):
        _close_dialog()
        st.rerun()

    if c2.button("Sauvegarder", type="primary", use_container_width=True, key="_form_save"):
        if not nom:
            st.warning("Le nom est obligatoire.")
        elif not courtier:
            st.warning("Le courtier / la banque est obligatoire.")
        else:
            _save_referentiel(courtier)
            if mode == "create":
                df, msg, msg_type = create_manual_asset(
                    df, nom, categorie, montant,
                    courtier=courtier, enveloppe=enveloppe,
                    immo_params=immo_params,
                )
            else:
                df, msg, msg_type = edit_manual_asset(
                    df, idx, row["id"], nom, categorie, montant,
                    courtier=courtier, enveloppe=enveloppe,
                    immo_params=immo_params,
                )
            flash_fn(msg, msg_type)
            _close_dialog()
            invalidate_cache_fn()
            st.rerun()

    return df


def _cancel_button():
    if st.button("Annuler", use_container_width=True, key="_form_cancel_early"):
        _close_dialog()
        st.rerun()


# ── Modale mise à jour datée ──────────────────────────────────────────────────

@st.dialog("Mettre à jour un montant", dismissible=False)
def _dialog_update(df, asset_id, invalidate_cache_fn, flash_fn):
    from datetime import date

    try:
        idx, row = _find_row_by_id(df, asset_id)
    except ValueError as e:
        st.error(str(e))
        if st.button("Fermer"):
            _close_dialog()
            st.rerun()
        return

    is_auto = row["categorie"] in CATEGORIES_AUTO
    ticker = row.get("ticker", "")

    st.caption(
        f"{row['nom']}" + (f" · {ticker}" if ticker else "")
    )

    op_date = st.date_input(
        "Date de l'opération",
        value=date.today(),
        key="_upd_date",
        help="Date réelle de l'opération, si différente d'aujourd'hui.",
    )

    if is_auto:
        quantite_actuelle = float(row.get("quantite") or 0.0)
        pru_actuel = float(row.get("pru") or 0.0)

        quantite = st.number_input(
            "Nouvelle quantité totale détenue",
            min_value=0.0,
            value=quantite_actuelle,
            step=1.0,
            format="%g",
            key="_upd_quantite",
        )
        pru = st.number_input(
            "Nouveau PRU (€)",
            min_value=0.0,
            value=pru_actuel,
            step=1.0,
            format="%g",
            key="_upd_pru",
            help="Prix de Revient Unitaire",
        )

    else:
        montant_actuel = float(row.get("montant") or 0.0)
        montant = st.number_input(
            "Montant total (€)",
            min_value=0.0,
            value=montant_actuel,
            step=100.0,
            key="_upd_montant",
        )

    c1, c2 = st.columns(2)
    if c1.button("Annuler", use_container_width=True, key="_upd_cancel"):
        _close_dialog()
        st.rerun()

    if c2.button("Enregistrer", type="primary", use_container_width=True, key="_upd_save"):
        if is_auto:
            with st.spinner("Enregistrement…"):
                df, msg, msg_type = update_at_date(
                    df, asset_id, row["categorie"],
                    op_date=op_date,
                    quantite=quantite,
                    pru=pru,
                )
        else:
            df, msg, msg_type = update_at_date(
                df, asset_id, row["categorie"],
                op_date=op_date,
                montant=montant,
            )
        flash_fn(msg, msg_type)
        _close_dialog()
        invalidate_cache_fn()
        st.rerun()


# ── Modales Streamlit (création / édition / suppression) ─────────────────────

@st.dialog("Ajouter un actif", dismissible=False,width="large")
def _dialog_create(df, invalidate_cache_fn, flash_fn):
    st.markdown("### Ajouter un actif")
    is_auto = st.toggle("Actif financier (ticker)", value=True, key="_form_is_auto")
    if is_auto:
        _form_auto(df, "create", None, None, invalidate_cache_fn, flash_fn)
    else:
        _form_manual(df, "create", None, None, invalidate_cache_fn, flash_fn)


@st.dialog("Editer un actif", dismissible=False)
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


@st.dialog("Supprimer un actif", dismissible=False)
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
    elif dtype == "update":
        _dialog_update(df, dialog["asset_id"], invalidate_cache_fn, flash_fn)