"""
ui/graphe_historique.py
───────────────────────
Affiche l'historique du patrimoine : sélecteur de période, courbes d'évolution
du patrimoine total et par catégorie.

Point d'entrée unique : render(df, df_hist, df_positions)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from services.historique import build_category_evolution
from services.pricer import fetch_historical_prices
from constants import CATEGORIES_AUTO, CATEGORY_COLOR_MAP, PLOTLY_LAYOUT, PERIOD_OPTIONS, PERIOD_DEFAULT, BENCHMARK_OPTIONS, BENCHMARK_COLOR


# ── Point d'entrée public ─────────────────────────────────────────────────────

def render(df: pd.DataFrame, df_hist: pd.DataFrame, df_positions: pd.DataFrame):
    auto_tickers = sorted(
        df[df["categorie"].isin(CATEGORIES_AUTO) & (df["ticker"] != "")]["ticker"]
        .dropna().unique().tolist()
    )

    has_history = not df_hist.empty or (not df_positions.empty and bool(auto_tickers))

    if not has_history:
        return

    st.subheader("Évolution", anchor=False)

    # ── Sélecteurs période + benchmark ───────────────────────────────────────
    col_period, col_benchmark = st.columns([5, 2])

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
            help="Comparer avec un indice de référence."
        )

    yf_period, nb_jours = PERIOD_OPTIONS[period_label]
    benchmark_ticker = BENCHMARK_OPTIONS[benchmark_label]

    start_date = None
    if nb_jours is not None:
        start_date = pd.Timestamp.today().normalize() - pd.Timedelta(days=nb_jours)

    with st.spinner("Reconstruction de l'historique…"):
        df_prices = fetch_historical_prices(tuple(auto_tickers), yf_period) if auto_tickers else pd.DataFrame()
        cat_evo = build_category_evolution(df, df_hist, df_positions, df_prices, tuple(CATEGORIES_AUTO))

        df_benchmark = pd.DataFrame()
        if benchmark_ticker:
            df_benchmark = fetch_historical_prices((benchmark_ticker,), yf_period)

    # Filtrage par période
    if start_date is not None:
        if not cat_evo.empty:
            cat_evo = cat_evo[cat_evo.index >= start_date]
        if not df_benchmark.empty:
            df_benchmark = df_benchmark[df_benchmark.index >= start_date]

    # ── Segmented control — catégories ───────────────────────────────────────
    CATEGORIES_EXCLUES_GRAPHE = {"Immobilier"}
    options_cat = [c for c in cat_evo.columns if c not in CATEGORIES_EXCLUES_GRAPHE] if not cat_evo.empty else []

    selected_cats = st.segmented_control(
        "Catégories",
        options=options_cat,
        selection_mode="multi",
        key="cat_selector",
    )

    # Aucune sélection = toutes les catégories
    active_cats = selected_cats if selected_cats else options_cat

    _render_chart(active_cats, cat_evo, df_benchmark, benchmark_ticker, benchmark_label)


def _render_chart(
    active_cats: list[str],
    cat_evo: pd.DataFrame,
    df_benchmark: pd.DataFrame,
    benchmark_ticker: str | None,
    benchmark_label: str,
):
    fig = go.Figure()

    # ── Aires empilées (catégories actives) ───────────────────────────────────
    if active_cats and not cat_evo.empty:
        for serie in active_cats:
            if serie not in cat_evo.columns:
                continue
            color = CATEGORY_COLOR_MAP.get(serie, "#CCCCCC")
            fig.add_trace(go.Scatter(
                x=cat_evo.index, y=cat_evo[serie],
                mode="lines", name=serie,
                stackgroup="patrimoine",
                line=dict(color=color, width=1),
                fillcolor=color,
            ))



    # ── Indice de comparaison ─────────────────────────────────────────────────
    if (
        benchmark_ticker
        and not df_benchmark.empty
        and benchmark_ticker in df_benchmark.columns
        and active_cats
        and not cat_evo.empty
    ):
        # Somme des catégories actives comme référence (pas le total global)
        cols_actives = [c for c in active_cats if c in cat_evo.columns]
        active_total = cat_evo[cols_actives].sum(axis=1).rename("total")

        bench_series = df_benchmark[benchmark_ticker].dropna()
        first_date = active_total.index[0]
        bench_series = bench_series[bench_series.index >= first_date]

        if not bench_series.empty:
            ref_bench = float(bench_series.iloc[0])
            candidates = active_total[active_total.index <= bench_series.index[0]]
            if candidates.empty:
                candidates = active_total
            ref_actif = float(candidates.iloc[-1])

            if ref_bench > 0:
                bench_scaled = bench_series * (ref_actif / ref_bench)
                fig.add_trace(go.Scatter(
                    x=bench_scaled.index,
                    y=bench_scaled.values,
                    mode="lines",
                    name=benchmark_label,
                    line=dict(color=BENCHMARK_COLOR, width=2, dash="dot"),
                ))

    fig.update_layout(
        **PLOTLY_LAYOUT,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)", font=dict(color="#E8EAF0", size=12)),
    )
    fig.update_yaxes(ticksuffix=" €", tickformat=",.0f")
    st.plotly_chart(fig, width="stretch", config={"staticPlot": True})