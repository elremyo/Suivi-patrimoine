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
from constants import CATEGORIES_AUTO, CATEGORY_COLOR_MAP, PLOTLY_LAYOUT, PERIOD_OPTIONS, PERIOD_DEFAULT, BENCHMARK_OPTIONS, BENCHMARK_COLOR


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
        st.info("Aucun historique disponible. Ajoute des actifs et mets à jour leurs montants pour construire un historique.")
        return

    # ── Sélecteurs ────────────────────────────────────────────────────────────
    col_period, col_benchmark = st.columns([4, 2])

    with col_period:
        period_label = st.radio(
            "Période",
            options=list(PERIOD_OPTIONS.keys()),
            index=list(PERIOD_OPTIONS.keys()).index(PERIOD_DEFAULT),
            horizontal=True,
            key="period_selector",
        )

    with col_benchmark:
        benchmark_label = st.selectbox(
            "Comparer avec",
            options=list(BENCHMARK_OPTIONS.keys()),
            index=0,
            key="benchmark_selector",
        )

    yf_period, nb_jours = PERIOD_OPTIONS[period_label]
    benchmark_ticker = BENCHMARK_OPTIONS[benchmark_label]

    # Calcul de la date de début pour le filtre
    start_date = None
    if nb_jours is not None:
        start_date = pd.Timestamp.today().normalize() - pd.Timedelta(days=nb_jours)

    with st.spinner("Reconstruction de l'historique…"):
        df_prices = fetch_historical_prices(tuple(auto_tickers), yf_period) if auto_tickers else pd.DataFrame()
        total_evo = build_total_evolution(df, df_hist, df_positions, df_prices, tuple(CATEGORIES_AUTO))
        cat_evo = build_category_evolution(df, df_hist, df_positions, df_prices, tuple(CATEGORIES_AUTO))

        # Récupération de l'indice de comparaison
        df_benchmark = pd.DataFrame()
        if benchmark_ticker:
            df_benchmark = fetch_historical_prices((benchmark_ticker,), yf_period)

    # Filtrage par période
    if start_date is not None:
        if not total_evo.empty:
            total_evo = total_evo[total_evo["date"] >= start_date]
        if not cat_evo.empty:
            cat_evo = cat_evo[cat_evo.index >= start_date]
        if not df_benchmark.empty:
            df_benchmark = df_benchmark[df_benchmark.index >= start_date]

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

    _render_chart(selected, total_evo, cat_evo, options_cat, df_benchmark, benchmark_ticker, benchmark_label)


def _render_chart(
    selected: list[str],
    total_evo: pd.DataFrame,
    cat_evo: pd.DataFrame,
    options_cat: list[str],
    df_benchmark: pd.DataFrame,
    benchmark_ticker: str | None,
    benchmark_label: str,
):
    """Construit et affiche le graphique Plotly des séries sélectionnées."""
    fig = go.Figure()

    for serie in selected:
        if serie == "Total patrimoine" and not total_evo.empty:
            fig.add_trace(go.Scatter(
                x=total_evo["date"], y=total_evo["total"],
                mode="lines+markers", name=serie,
                line=dict(color="#E8EAF0", width=2),
                marker=dict(size=5),
            ))
        elif serie in options_cat and not cat_evo.empty and serie in cat_evo.columns:
            color = CATEGORY_COLOR_MAP.get(serie, "#CCCCCC")
            fig.add_trace(go.Scatter(
                x=cat_evo.index, y=cat_evo[serie],
                mode="lines+markers", name=serie,
                line=dict(color=color, width=2),
                marker=dict(size=5),
            ))

    # ── Indice de comparaison ─────────────────────────────────────────────────
    if (
        benchmark_ticker
        and not df_benchmark.empty
        and benchmark_ticker in df_benchmark.columns
        and not total_evo.empty
        and "Total patrimoine" in selected
    ):
        bench_series = df_benchmark[benchmark_ticker].dropna()

        if not bench_series.empty and not total_evo.empty:
            total_evo_indexed = total_evo.set_index("date")["total"]

            # Le benchmark ne commence pas avant la première donnée patrimoine
            first_patrimoine_date = total_evo_indexed.index[0]
            bench_series = bench_series[bench_series.index >= first_patrimoine_date]

            if not bench_series.empty:
                ref_bench = float(bench_series.iloc[0])

                # Valeur patrimoine au point de départ du benchmark
                candidates = total_evo_indexed[total_evo_indexed.index <= bench_series.index[0]]
                if candidates.empty:
                    candidates = total_evo_indexed
                ref_patrimoine = float(candidates.iloc[-1])

            # Recalage : l'indice démarre au niveau du patrimoine
            if ref_bench > 0:
                bench_scaled = bench_series * (ref_patrimoine / ref_bench)

                fig.add_trace(go.Scatter(
                    x=bench_scaled.index,
                    y=bench_scaled.values,
                    mode="lines",
                    name=benchmark_label,
                    line=dict(color=BENCHMARK_COLOR, width=2, dash="dot"),
                ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(color="#E8EAF0")),
    )
    fig.update_yaxes(
        ticksuffix=" €",
        tickformat=",.0f"
    )
    st.plotly_chart(fig, width="stretch", config={"staticPlot": True})