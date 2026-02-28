"""
ui/tab_historique.py
───────────────────────
Contenu du tab "📈 Historique" : sélecteur de période, courbes d'évolution
du patrimoine total et par catégorie.

Point d'entrée unique : render(df, df_hist, df_positions)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from services.historique import build_total_evolution, build_category_evolution
from services.pricer import fetch_historical_prices
from constants import CATEGORIES_AUTO, CATEGORY_COLOR_MAP, PLOTLY_LAYOUT, PERIOD_OPTIONS, PERIOD_DEFAULT

# ── Point d'entrée public ─────────────────────────────────────────────────────

def render(df: pd.DataFrame, df_hist: pd.DataFrame, df_positions: pd.DataFrame):
    """
    Affiche le contenu complet du tab Historique.

    Paramètres :
    - df           : DataFrame des actifs courants
    - df_hist      : historique des montants manuels
    - df_positions : historique des positions (actifs auto)
    """
    auto_tickers = sorted(
        df[df["categorie"].isin(CATEGORIES_AUTO) & (df["ticker"] != "")]["ticker"]
        .dropna().unique().tolist()
    )

    has_history = not df_hist.empty or (not df_positions.empty and bool(auto_tickers))

    if not has_history:
        st.info("Aucun historique disponible. Ajoutez des actifs et mettez à jour leurs montants pour construire un historique.")
        return

    # Sélecteur de période
    period_label = st.segmented_control(
        "Période",
        options=list(PERIOD_OPTIONS.keys()),
        default=PERIOD_DEFAULT,
        key="period_selector",
    )
    yf_period, nb_jours = PERIOD_OPTIONS[period_label]

    # Calcul de la date de début pour le filtre
    start_date = None
    if nb_jours is not None:
        start_date = pd.Timestamp.today().normalize() - pd.Timedelta(days=nb_jours)

    with st.spinner("Reconstruction de l'historique…"):
        df_prices = fetch_historical_prices(tuple(auto_tickers), yf_period) if auto_tickers else pd.DataFrame()
        total_evo = build_total_evolution(df, df_hist, df_positions, df_prices, tuple(CATEGORIES_AUTO))
        cat_evo = build_category_evolution(df, df_hist, df_positions, df_prices, tuple(CATEGORIES_AUTO))

    # Filtrage par période
    if start_date is not None:
        if not total_evo.empty:
            total_evo = total_evo[total_evo["date"] >= start_date]
        if not cat_evo.empty:
            cat_evo = cat_evo[cat_evo.index >= start_date]

    # Sélecteur de séries
    options_total = ["Total patrimoine"]
    options_cat = list(cat_evo.columns) if not cat_evo.empty else []
    all_options = options_total + options_cat

    selected = st.multiselect(
        "Séries à afficher",
        options=all_options,
        default=all_options,
        placeholder="Choisir au moins une série…",
    )

    if not selected:
        st.info("Sélectionne au moins une série à afficher.")
        return

    _render_chart(selected, total_evo, cat_evo, options_cat)


def _render_chart(
    selected: list[str],
    total_evo: pd.DataFrame,
    cat_evo: pd.DataFrame,
    options_cat: list[str],
):
    """Construit et affiche le graphique Plotly des séries sélectionnées."""
    fig = go.Figure()

    for serie in selected:
        if serie == "Total patrimoine" and not total_evo.empty:
            # Couleur neutre fixe pour le total
            fig.add_trace(go.Scatter(
                x=total_evo["date"], y=total_evo["total"],
                mode="lines+markers", name=serie,
                line=dict(color="#E8EAF0", width=2),
                marker=dict(size=5),
            ))
        elif serie in options_cat and not cat_evo.empty and serie in cat_evo.columns:
            # Couleur fixe par catégorie
            color = CATEGORY_COLOR_MAP.get(serie, "#CCCCCC")
            fig.add_trace(go.Scatter(
                x=cat_evo.index, y=cat_evo[serie],
                mode="lines+markers", name=serie,
                line=dict(color=color, width=2),
                marker=dict(size=5),
            ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        yaxis_title="Montant (€)", xaxis_title="Date",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(color="#E8EAF0")),
    )
    st.plotly_chart(fig, width="stretch", config={"staticPlot": True})