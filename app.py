"""
app.py
──────
Point d'entrée de l'application Streamlit.
"""

import streamlit as st
import pandas as pd
from services.storage import init_storage
from services.assets import get_assets
from services.historique import init_historique, load_historique, build_total_evolution, build_category_evolution
from services.positions import init_positions, load_positions
from ui.tab_actifs import render as render_actifs
from ui.tab_historique import render as render_historique
from ui.tab_repartition import render as render_repartition
from ui.asset_form import render_active_dialog
from ui.sidebar import render as render_sidebar
from services.demo_mode import is_demo_mode


st.set_page_config(page_title="Suivi de patrimoine", layout="wide", page_icon=":material/finance_mode:")


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


df           = cached_load_assets()
df_hist      = cached_load_historique()
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

render_sidebar(df, invalidate_data_cache, flash)


# ── Modales ───────────────────────────────────────────────────────────────────

render_active_dialog(df, invalidate_data_cache, flash)


# ── Page principale ───────────────────────────────────────────────────────────

show_flash()

st.logo(image=":material/finance_mode:", size="large", icon_image=":material/finance_mode:")

st.title("Suivi de patrimoine", anchor=False)

if is_demo_mode():
    st.info("Mode démo. Pour le quitter, utilisez le menu de gauche.", icon="👀")

tab_actifs, tab_repartition, tab_historique = st.tabs(["📋 Actifs", "📊 Répartition", "📈 Historique"])

with tab_actifs:
    render_actifs(df, invalidate_data_cache, flash)

with tab_repartition:
    render_repartition(df)

with tab_historique:
    render_historique(df, df_hist, df_positions)