"""
ui/tab_actifs.py
───────────────────
Contenu du tab "📋 Actifs" : liste des actifs, total patrimoine.
Les modales sont gérées via ui/asset_form.py.
Les graphiques de répartition sont dans ui/tab_repartition.py.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from services.asset_manager import refresh_prices
from services.storage import (
    download_assets, download_historique, download_positions,
    import_assets, import_historique, import_positions,
)
from ui.asset_form import set_dialog_create, set_dialog_edit, set_dialog_delete
from constants import CATEGORIES_ASSETS, CATEGORIES_AUTO, CATEGORY_COLOR_MAP, PLOTLY_LAYOUT


# ── Ligne d'actif ─────────────────────────────────────────────────────────────

def _render_asset_row(row: pd.Series):
    is_auto_row = row["categorie"] in CATEGORIES_AUTO
    cols = st.columns([4, 2, 2, 2, 1, 1])

    # ── Colonne nom + infos discrètes ─────────────────────────────────────────
    courtier  = str(row.get("courtier",  "") or "").strip()
    enveloppe = str(row.get("enveloppe", "") or "").strip()
    meta_parts = [p for p in [courtier, enveloppe] if p]
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

    # ── Boutons ───────────────────────────────────────────────────────────────
    if cols[4].button("", key=f"mod_{row['id']}", icon=":material/edit_square:"):
        set_dialog_edit(row["id"])
        st.rerun()

    if cols[5].button("", key=f"del_{row['id']}", icon=":material/delete:"):
        set_dialog_delete(row["id"])
        st.rerun()


# ── Section sauvegarde ────────────────────────────────────────────────────────

def _render_backup_section(df: pd.DataFrame, invalidate_cache_fn, flash_fn):
    """Affiche les boutons d'export et les zones d'import en bas de l'onglet."""
    st.divider()
    st.subheader("Sauvegarde", anchor=False)

    # ── Export ────────────────────────────────────────────────────────────────
    st.caption("Télécharger")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.download_button(
            "Actifs",
            data=download_assets(df),
            file_name="patrimoine.csv",
            mime="text/csv",
            icon=":material/download:",
            use_container_width=True,
            key="btn_dl_assets",
        )

    with col2:
        st.download_button(
            "Historique",
            data=download_historique(),
            file_name="historique.csv",
            mime="text/csv",
            icon=":material/download:",
            use_container_width=True,
            key="btn_dl_historique",
        )

    with col3:
        st.download_button(
            "Positions",
            data=download_positions(),
            file_name="positions.csv",
            mime="text/csv",
            icon=":material/download:",
            use_container_width=True,
            key="btn_dl_positions",
        )

    # ── Import ────────────────────────────────────────────────────────────────
    st.caption("Importer — remplace toutes les données existantes")

    col1, col2, col3 = st.columns(3)

    with col1:
        f = st.file_uploader("Actifs", type="csv", label_visibility="collapsed",
                             key=f"up_assets_{st.session_state.get('_up_assets_v', 0)}")
        if f:
            ok, msg = import_assets(f)
            flash_fn(msg, "success" if ok else "error")
            st.session_state["_up_assets_v"] = st.session_state.get("_up_assets_v", 0) + 1
            if ok:
                invalidate_cache_fn()
            st.rerun()

    with col2:
        f = st.file_uploader("Historique", type="csv", label_visibility="collapsed",
                             key=f"up_historique_{st.session_state.get('_up_historique_v', 0)}")
        if f:
            ok, msg = import_historique(f)
            flash_fn(msg, "success" if ok else "error")
            st.session_state["_up_historique_v"] = st.session_state.get("_up_historique_v", 0) + 1
            if ok:
                invalidate_cache_fn()
            st.rerun()

    with col3:
        f = st.file_uploader("Positions", type="csv", label_visibility="collapsed",
                             key=f"up_positions_{st.session_state.get('_up_positions_v', 0)}")
        if f:
            ok, msg = import_positions(f)
            flash_fn(msg, "success" if ok else "error")
            st.session_state["_up_positions_v"] = st.session_state.get("_up_positions_v", 0) + 1
            if ok:
                invalidate_cache_fn()
            st.rerun()


# ── Point d'entrée public ─────────────────────────────────────────────────────

def render(df: pd.DataFrame, invalidate_cache_fn, flash_fn) -> pd.DataFrame:
    from services.assets import compute_total

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

    # Affichage du total
    total = compute_total(df)
    st.metric(label="Patrimoine total", value=f"{total:,.2f} €")

    # Affichage des boutons d'action
    with st.container(horizontal=True, vertical_alignment="center"):
        with st.container(horizontal=True, vertical_alignment="center"):
            if st.button(
                    "",
                    icon=":material/refresh:",
                    disabled=not has_auto_assets,
                    help="Actualiser les prix",
                    key="btn_refresh_prices",
                    type="tertiary"
                ):
                    with st.spinner("Récupération des prix…"):
                        df, msg, msg_type = refresh_prices(df)
                    flash_fn(msg, msg_type)
                    st.session_state["sync_time"] = datetime.now().strftime("%H:%M")
                    st.session_state["sync_error_tickers"] = set(
                        msg.replace("Tickers introuvables : ", "").split(", ")
                    ) if msg_type == "warning" else set()
                    invalidate_cache_fn()
                    st.rerun()
            if has_auto_assets and "sync_time" in st.session_state:
                st.caption(f"Prix synchronisés à {st.session_state['sync_time']}")

        if st.button(
            "Compléter mon patrimoine",
            icon=":material/add:",
            type="primary",
            key="btn_add_asset",
        ):
            set_dialog_create()
            st.rerun()

    # ── Liste des actifs ──────────────────────────────────────────────────────
    if df.empty:
        st.info("Aucun actif enregistré. Utilisez le bouton ＋ pour commencer.")
    else:
        categories_presentes = [c for c in CATEGORIES_ASSETS if c in df["categorie"].values]

        for categorie in categories_presentes:
            category_color = CATEGORY_COLOR_MAP.get(categorie, "#CCCCCC")
            st.markdown(
                f"<span style='color:{category_color}; font-size:0.85em;'>●</span> "
                f"<span style='color:{category_color}; font-size:0.85em; text-transform:uppercase; letter-spacing:0.08em;'>{categorie}</span>",
                unsafe_allow_html=True,
            )
            df_cat = df[df["categorie"] == categorie]
            for _, row in df_cat.iterrows():
                with st.container(border=True, vertical_alignment="center"):
                    _render_asset_row(row)
            st.space(size="small")

    # ── Sauvegarde ────────────────────────────────────────────────────────────
    _render_backup_section(df, invalidate_cache_fn, flash_fn)

    return df