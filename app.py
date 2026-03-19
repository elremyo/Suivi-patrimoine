"""
app.py
──────
Point d'entrée de l'application Streamlit.
"""

import streamlit as st
import pandas as pd
from services.db import init_db
from services.assets import get_assets
from services.asset_manager import refresh_prices
from services.historique import init_historique, load_historique, build_total_evolution, build_category_evolution, build_asset_evolution
from services.positions import init_positions, load_positions
from ui.tab_synthese import render as render_synthese
from ui.tab_actifs import render as render_actifs
from ui.tab_emprunts import render as render_emprunts
from ui.tab_parametres import render as render_parametres
from ui.asset_form import render_active_dialog, set_dialog_create
from ui.forms.form_emprunt import set_emprunt_dialog_create, render_emprunt_dialog
from constants import CATEGORIES_AUTO
from datetime import datetime



st.set_page_config(page_title="Suivi de patrimoine", layout="wide", page_icon=":material/finance_mode:", initial_sidebar_state="collapsed")


init_db()
init_historique()
init_positions()

# ── Cache des lectures ────────────────────────────────────────────────────────

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
    build_asset_evolution.clear()


df           = cached_load_assets()
df_hist      = cached_load_historique()
df_positions = cached_load_positions()


# ── Refresh automatique des prix au démarrage de session ─────────────────────

_has_auto = (
    not df.empty
    and df["categorie"].isin(CATEGORIES_AUTO).any()
    and df["ticker"].notna().any()
    and (df["ticker"] != "").any()
)

if "prices_refreshed" not in st.session_state and _has_auto:
    with st.spinner("Actualisation des prix en cours…"):
        df, _msg, _msg_type = refresh_prices(df)
    st.session_state["prices_refreshed"] = True
    st.session_state["sync_time"] = datetime.now().strftime("%H:%M")
    st.session_state["sync_error_tickers"] = (
        set(_msg.replace("Tickers introuvables : ", "").split(", "))
        if _msg_type == "warning" else set()
    )
    if _msg_type != "success":
        flash(_msg, _msg_type)
    invalidate_data_cache()
    st.rerun()


# ── Utilitaires UI ────────────────────────────────────────────────────────────

def flash(msg: str, type: str = "success"):
    st.session_state["_flash"] = {"msg": msg, "type": type}

def show_flash():
    if "_flash" in st.session_state:
        f = st.session_state.pop("_flash")
        icons = {"success": "✅", "warning": "⚠️", "error": "❌", "info": "ℹ️"}
        st.toast(f["msg"], icon=icons.get(f["type"], "ℹ️"))


# ── Modales ───────────────────────────────────────────────────────────────────

render_active_dialog(df, invalidate_data_cache, flash)
render_emprunt_dialog(flash)


# ── Page principale ───────────────────────────────────────────────────────────

show_flash()

st.logo(image=":material/finance_mode:", size="large", icon_image=":material/finance_mode:")

with st.container(horizontal=True, vertical_alignment="bottom", horizontal_alignment="right"):
    st.title("Suivi de patrimoine", anchor=False)
    with st.popover("Compléter mon patrimoine", type="primary", icon=":material/add:"):
        for label, icon, categorie in [
            ("Actions & Fonds", ":material/candlestick_chart:", "Actions & Fonds"),
            ("Crypto",          ":material/currency_bitcoin:", "Crypto"),
            ("Livret",          ":material/savings:",          "Livrets"),
            ("Immobilier",      ":material/home:",             "Immobilier"),
            ("Fonds euros",     ":material/shield:",           "Fonds euros"),
        ]:
            if st.button(label, use_container_width=True, icon=icon, key=f"add_{categorie}"):
                set_dialog_create(categorie)
                st.rerun()
        if st.button("Crédit / Emprunt", use_container_width=True, icon=":material/credit_card:", key="add_passif"):
            set_emprunt_dialog_create()
            st.rerun()


tab_synthese, tab_actifs, tab_passifs, tab_params = st.tabs([
    "Synthèse", "Actifs", "Passifs", "Paramètres"
])

with tab_synthese:
    render_synthese(df, df_hist, df_positions)

with tab_actifs:
    render_actifs(df, invalidate_data_cache, flash)

with tab_passifs:
    render_emprunts(flash)

with tab_params:
    render_parametres(df, invalidate_data_cache)