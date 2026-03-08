"""
ui/tab_actifs.py
───────────────────
Contenu du tab "Actifs" : liste des actifs.
Les métriques globales (total actifs / passifs / net) sont dans tab_synthese.py.
Les modales sont gérées via ui/asset_form.py.
Les exports, imports, mode démo et réinitialisation sont dans ui/sidebar.py.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from services.asset_manager import refresh_prices
from ui.asset_form import set_dialog_create, set_dialog_edit, set_dialog_delete, set_dialog_update
from constants import CATEGORIES_ASSETS, CATEGORIES_AUTO, CATEGORY_COLOR_MAP
from services.demo_mode import is_demo_mode, activate_demo, deactivate_demo
from constants import DEMO_USER_NAME


# ── Ligne d'actif ─────────────────────────────────────────────────────────────

def _render_asset_row(row: pd.Series):
    is_auto_row = row["categorie"] in CATEGORIES_AUTO
    cols = st.columns([4, 2, 2, 2, 0.5, 0.5, 0.5])

    # ── Colonne nom + infos discrètes ─────────────────────────────────────────
    courtier_val = row.get("courtier", "")
    courtier = "" if pd.isna(courtier_val) else str(courtier_val).strip()
    enveloppe_val = row.get("enveloppe", "")
    enveloppe = "" if pd.isna(enveloppe_val) else str(enveloppe_val).strip()
    meta_parts = [p for p in (courtier, enveloppe) if p]
    meta_str   = " · ".join(meta_parts)

    if is_auto_row and row.get("ticker"):
        error_tickers = st.session_state.get("sync_error_tickers", set())
        ticker = row["ticker"]
        if ticker in error_tickers:
            icon = ":red[:material/sync_problem:]"
        else:
            icon = ":green[:material/published_with_changes:]"
        ticker_line = f"{ticker}"
        if meta_str:
            ticker_line += f" · {meta_str}"
        cols[0].write(row["nom"])
        cols[0].markdown(f"{icon} :small[:grey[{ticker_line}]]")
    else:
        cols[0].write(row["nom"])
        if meta_str:
            cols[0].caption(meta_str)
        if row["categorie"] == "Immobilier":
            immo_parts = []
            if row.get("type_bien") and str(row.get("type_bien")).strip() and str(row.get("type_bien")) != "autre":
                immo_parts.append(str(row.get("type_bien")).strip())
            if row.get("superficie_m2") and float(row.get("superficie_m2", 0) or 0) > 0:
                immo_parts.append(f"{float(row['superficie_m2']):.0f} m²")
            if row.get("adresse") and str(row.get("adresse")).strip():
                immo_parts.append(str(row.get("adresse")).strip())
            if immo_parts:
                cols[0].caption(" · ".join(immo_parts))

    # ── Quantité (actifs auto uniquement) ─────────────────────────────────────
    if is_auto_row:
        cols[1].caption(f'{row["quantite"]:g} unités')

    # ── Montant ───────────────────────────────────────────────────────────────
    cols[2].write(f"{row['montant']:,.2f} €")

    # ── PnL (actifs auto avec PRU) ────────────────────────────────────────────
    if is_auto_row and row.get("quantite", 0) > 0 and row.get("pru", 0) > 0:
        valeur_achat = row["pru"] * row["quantite"]
        pnl = row["montant"] - valeur_achat
        pnl_pct = (pnl / valeur_achat * 100) if valeur_achat else 0
        sign_color = "green" if pnl >= 0 else "red"
        sign = "+" if pnl >= 0 else ""
        sign_icon = ":material/trending_up:" if pnl >= 0 else ":material/trending_down:"
        cols[3].markdown(f":{sign_color}-badge[{sign_icon} {sign}{pnl:,.2f} € ({sign}{pnl_pct:.1f}%)]")

    # ── Bouton mise à jour datée ──────────────────────────────────────────────
    if cols[4].button(
        "",
        key=f"upd_{row['id']}",
        icon=":material/history:",
        help="Mettre à jour à une date",
    ):
        set_dialog_update(row["id"])
        st.rerun()

    # ── Boutons édition / suppression ─────────────────────────────────────────
    if cols[5].button("", key=f"mod_{row['id']}", icon=":material/edit_square:", help="Modifier l'actif"):
        set_dialog_edit(row["id"])
        st.rerun()

    if cols[6].button("", key=f"del_{row['id']}", icon=":material/delete:", help="Supprimer l'actif"):
        set_dialog_delete(row["id"])
        st.rerun()


# ── Point d'entrée public ─────────────────────────────────────────────────────

def render(df: pd.DataFrame, invalidate_cache_fn, flash_fn) -> pd.DataFrame:

    has_auto_assets = (
        not df.empty
        and df["categorie"].isin(CATEGORIES_AUTO).any()
        and df["ticker"].notna().any()
        and (df["ticker"] != "").any()
    )

    if "prices_refreshed" not in st.session_state and has_auto_assets:
        with st.spinner("Actualisation des prix en cours…"):
            df, msg, msg_type = refresh_prices(df)
        st.session_state["prices_refreshed"] = True
        st.session_state["sync_time"] = datetime.now().strftime("%H:%M")
        st.session_state["sync_error_tickers"] = set(
            msg.replace("Tickers introuvables : ", "").split(", ")
        ) if msg_type == "warning" else set()
        if msg_type != "success":
            flash_fn(msg, msg_type)
        invalidate_cache_fn()
        st.rerun()

    if has_auto_assets and "sync_time" not in st.session_state:
        st.session_state["sync_time"] = datetime.now().strftime("%H:%M")
        st.session_state["sync_error_tickers"] = set()

    # ── Barre d'actions ───────────────────────────────────────────────────────
    col_btn, col_sync = st.columns([6, 2], vertical_alignment="center")

    with col_btn:
        if st.button("+ Ajouter un actif", type="primary", key="btn_add_asset"):
            set_dialog_create()
            st.rerun()

    if has_auto_assets:
        sync_time = st.session_state.get("sync_time", "")
        with col_sync:
            st.caption(f":grey[Dernière synchro : {sync_time}]" if sync_time else "")

    st.space(size="small")

    # ── Liste des actifs ──────────────────────────────────────────────────────
    if df.empty:
        st.info("Aucun actif pour l'instant. Clique sur « + Ajouter un actif » pour commencer.")
        return df

    for _, row in df.iterrows():
        with st.container(border=True):
            _render_asset_row(row)

    return df