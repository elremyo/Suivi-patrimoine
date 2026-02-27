"""
app.py
──────
Point d'entrée de l'application Streamlit.
Responsabilités limitées à :
- Configuration et initialisation
- Cache des lectures CSV
- Sidebar (ajout d'actif, rafraîchissement des prix, export)
- Routing vers les tabs (tab_actifs, tab_historique)

Toute la logique métier est dans services/asset_manager.py.
Tout le rendu des tabs est dans pages/tab_actifs.py et pages/tab_historique.py.
"""

import streamlit as st
import pandas as pd
from services.storage import init_storage, download_assets
from services.assets import get_assets
from services.historique import init_historique, load_historique
from services.positions import init_positions, load_positions
from services.asset_manager import create_auto_asset, create_manual_asset, refresh_prices
from pages.tab_actifs import render as render_actifs
from pages.tab_historique import render as render_historique
from constants import CATEGORIES_ASSETS, CATEGORIES_AUTO


st.set_page_config(page_title="Suivi Patrimoine", layout="wide")
init_storage()
init_historique()
init_positions()


# ── Cache des lectures CSV ────────────────────────────────────────────────────
# Ces fonctions ne relisent le disque qu'une seule fois par session Streamlit.
# Appeler invalidate_data_cache() après chaque écriture pour forcer un rechargement.

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
    """Vide le cache des lectures CSV. À appeler après toute écriture sur le disque."""
    cached_load_assets.clear()
    cached_load_historique.clear()
    cached_load_positions.clear()


df = cached_load_assets()
df_hist = cached_load_historique()
df_positions = cached_load_positions()


# ── Utilitaires UI ────────────────────────────────────────────────────────────

def flash(msg: str, type: str = "success"):
    """Stocke un message à afficher après le prochain rerun."""
    st.session_state["_flash"] = {"msg": msg, "type": type}


def show_flash():
    """Affiche et consomme le message flash s'il existe."""
    if "_flash" in st.session_state:
        f = st.session_state.pop("_flash")
        icons = {"success": "✅", "warning": "⚠️", "error": "❌", "info": "ℹ️"}
        st.toast(f["msg"], icon=icons.get(f["type"], "ℹ️"))


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("Suivi de patrimoine")
    st.divider()

    st.subheader("Ajouter un actif")

    categorie = st.selectbox("Catégorie", options=CATEGORIES_ASSETS, key="add_categorie")
    is_auto = categorie in CATEGORIES_AUTO

    with st.form("add_asset", clear_on_submit=True):
        if is_auto:
            ticker = st.text_input("Ticker *", placeholder="ex. AAPL, BTC-USD, CW8.PA").strip().upper()
            quantite = st.number_input("Quantité", min_value=0.0, step=1.0, format="%g")
            pru = st.number_input("PRU (€)", min_value=0.0, step=1.0, format="%g",
                                  help="Prix de Revient Unitaire.")
        else:
            nom = st.text_input("Nom *")
            montant = st.number_input("Montant (€)", min_value=0.0, step=100.0)

        if st.form_submit_button("Ajouter", type="primary", use_container_width=True):
            if is_auto and not ticker:
                st.warning("Le ticker est obligatoire.")
            elif not is_auto and not nom:
                st.warning("Le nom est obligatoire.")
            else:
                if is_auto:
                    with st.spinner("Récupération du nom et du prix…"):
                        df, msg, msg_type = create_auto_asset(df, ticker, quantite, pru, categorie)
                else:
                    df, msg, msg_type = create_manual_asset(df, nom, categorie, montant)
                flash(msg, msg_type)
                # ✅ Invalide le cache avant le rerun (Action 2)
                invalidate_data_cache()
                st.rerun()

    show_flash()

    st.divider()

    st.subheader("Prix")

    has_auto_assets = (
        not df.empty
        and df["categorie"].isin(CATEGORIES_AUTO).any()
        and df["ticker"].notna().any()
        and (df["ticker"] != "").any()
    )

    if st.button("🔄 Actualiser les prix", disabled=not has_auto_assets, width="stretch"):
        with st.spinner("Récupération des prix…"):
            df, msg, msg_type = refresh_prices(df)
        flash(msg, msg_type)
        # ✅ Invalide le cache : les prix ont été mis à jour sur le disque (Action 2)
        invalidate_data_cache()
        st.rerun()

    show_flash()

    st.divider()

    st.subheader("Exporter")
    st.download_button(
        "Télécharger le patrimoine",
        data=download_assets(df),
        file_name="patrimoine.csv",
        mime="text/csv",
        icon=":material/download:",
        use_container_width=True,
    )


# ── Page principale ───────────────────────────────────────────────────────────

st.title("Suivi de patrimoine")

tab_actifs, tab_historique = st.tabs(["📋 Actifs", "📈 Historique"])

with tab_actifs:
    render_actifs(df, invalidate_data_cache, flash)

with tab_historique:
    render_historique(df, df_hist, df_positions)