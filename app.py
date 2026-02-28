"""
app.py
──────
Point d'entrée de l'application Streamlit.
"""

import streamlit as st
import pandas as pd
from services.storage import init_storage, download_assets
from services.assets import get_assets
from services.historique import init_historique, load_historique, build_total_evolution, build_category_evolution
from services.positions import init_positions, load_positions
from services.asset_manager import refresh_prices
from ui.tab_actifs import render as render_actifs
from ui.tab_historique import render as render_historique
from ui.asset_form import set_dialog_create, render_active_dialog
from constants import CATEGORIES_AUTO


st.set_page_config(page_title="Suivi Patrimoine", layout="wide")
init_storage()
init_historique()
init_positions()


# ── Cache des lectures CSV ────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def cached_load_assets() -> pd.DataFrame:
    return get_assets()

@st.cache_data(show_spinner=False)
def cached_load_historique() -> pd.DataFrame:
    return load_historique()

@st.cache_data(show_spinner=False)
def cached_load_positions() -> pd.DataFrame:
    return load_positions()

def invalidate_data_cache():
    cached_load_assets.clear()
    cached_load_historique.clear()
    cached_load_positions.clear()
    build_total_evolution.clear()
    build_category_evolution.clear()


df          = cached_load_assets()
df_hist     = cached_load_historique()
df_positions = cached_load_positions()


# ── Utilitaires UI ────────────────────────────────────────────────────────────

def flash(msg: str, type: str = "success"):
    st.session_state["_flash"] = {"msg": msg, "type": type}

def show_flash():
    if "_flash" in st.session_state:
        f = st.session_state.pop("_flash")
        icons = {"success": "✅", "warning": "⚠️", "error": "❌", "info": "ℹ️"}
        st.toast(f["msg"], icon=icons.get(f["type"], "ℹ️"))


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("Suivi de patrimoine",anchor=False)
    st.divider()

    if st.button("Ajouter un actif", type="primary", use_container_width=True, icon=":material/add:"):
        set_dialog_create()
        st.rerun()

    st.divider()

    has_auto_assets = (
        not df.empty
        and df["categorie"].isin(CATEGORIES_AUTO).any()
        and df["ticker"].notna().any()
        and (df["ticker"] != "").any()
    )

    if st.button("Actualiser les prix", disabled=not has_auto_assets, use_container_width=True, icon=":material/refresh:"):
        with st.spinner("Récupération des prix…"):
            df, msg, msg_type = refresh_prices(df)
        flash(msg, msg_type)
        invalidate_data_cache()
        st.rerun()

    st.divider()

    st.download_button(
        "Télécharger le patrimoine",
        data=download_assets(df),
        file_name="patrimoine.csv",
        mime="text/csv",
        use_container_width=True,
        icon=":material/download:",
    )

    show_flash()


# ── Modales ───────────────────────────────────────────────────────────────────
# Un seul appel, une seule modale possible à la fois.

render_active_dialog(df, invalidate_data_cache, flash)


# ── Page principale ───────────────────────────────────────────────────────────

st.logo(image=":material/finance_mode:", size="large",icon_image=":material/finance_mode:")

st.title("Suivi de patrimoine",anchor=False)

tab_actifs, tab_historique = st.tabs(["📋 Actifs", "📈 Historique"])

with tab_actifs:
    render_actifs(df, invalidate_data_cache, flash)

with tab_historique:
    render_historique(df, df_hist, df_positions)