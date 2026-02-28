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
from services.asset_manager import create_auto_asset, create_manual_asset, refresh_prices
from services.pricer import validate_ticker, lookup_ticker
from ui.tab_actifs import render as render_actifs
from ui.tab_historique import render as render_historique
from constants import CATEGORIES_ASSETS, CATEGORIES_AUTO


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


df = cached_load_assets()
df_hist = cached_load_historique()
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
    st.title("Suivi de patrimoine")
    st.divider()

    st.subheader("Ajouter un actif")

    with st.container(border=True):

        categorie = st.selectbox("Catégorie", options=CATEGORIES_ASSETS, key="add_categorie")
        is_auto = categorie in CATEGORIES_AUTO

        # Si on change de catégorie, on réinitialise l'aperçu du ticker
        if st.session_state.get("_last_add_categorie") != categorie:
            st.session_state.pop("ticker_preview", None)
            st.session_state["_last_add_categorie"] = categorie

        if is_auto:
            # ── Étape 1 : saisie et vérification du ticker ────────────────────────
            ticker_input = st.text_input(
                "Ticker *",
                placeholder="ex. AAPL, BTC-USD, CW8.PA",
                key="add_ticker_input",
            ).strip().upper()

            # Si le ticker saisi change, on efface l'aperçu précédent
            if st.session_state.get("_last_ticker_input") != ticker_input:
                st.session_state.pop("ticker_preview", None)
                st.session_state["_last_ticker_input"] = ticker_input

            if st.button("🔍 Vérifier le ticker", use_container_width=True):
                valid, err = validate_ticker(ticker_input)
                if not valid:
                    st.error(err)
                else:
                    with st.spinner("Recherche en cours…"):
                        result = lookup_ticker(ticker_input)
                    if result:
                        st.session_state["ticker_preview"] = result
                    else:
                        st.error(f"Ticker « {ticker_input} » introuvable sur yfinance. Vérifiez l'orthographe.")

            # ── Étape 2 : aperçu + confirmation ──────────────────────────────────
            if "ticker_preview" in st.session_state:
                preview = st.session_state["ticker_preview"]

                with st.container(border=True):
                    st.markdown(f"**{preview['name']}**")
                    price_str = f"{preview['price']:,.4f} {preview['currency']}".strip()
                    st.caption(f"{preview['ticker']} · {price_str}")

                quantite = st.number_input("Quantité", min_value=0.0, step=1.0, format="%g", key="add_quantite")
                pru = st.number_input("PRU (€)", min_value=0.0, step=1.0, format="%g",
                                      help="Prix de Revient Unitaire.", key="add_pru")

                c1, c2 = st.columns(2)
                if c1.button("✅ Confirmer", type="primary", use_container_width=True):
                    with st.spinner("Ajout en cours…"):
                        df, msg, msg_type = create_auto_asset(
                            df, preview["ticker"], quantite, pru, categorie
                        )
                    st.session_state.pop("ticker_preview", None)
                    flash(msg, msg_type)
                    invalidate_data_cache()
                    st.rerun()
                if c2.button("Annuler", use_container_width=True):
                    st.session_state.pop("ticker_preview", None)
                    st.rerun()

        else:
            # ── Actif manuel : formulaire classique ───────────────────────────────
            with st.form("add_manual_asset", clear_on_submit=True):
                nom = st.text_input("Nom *")
                montant = st.number_input("Montant (€)", min_value=0.0, step=100.0)

                if st.form_submit_button("Ajouter", type="primary", use_container_width=True):
                    if not nom:
                        st.warning("Le nom est obligatoire.")
                    else:
                        df, msg, msg_type = create_manual_asset(df, nom, categorie, montant)
                        flash(msg, msg_type)
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