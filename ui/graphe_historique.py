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
from services.historique import build_category_evolution, _compute_raw_evolution
from services.pricer import fetch_historical_prices
from constants import CATEGORIES_AUTO, CATEGORY_COLOR_MAP, PLOTLY_LAYOUT, PERIOD_OPTIONS, PERIOD_DEFAULT, BENCHMARK_OPTIONS, BENCHMARK_COLOR


# ── Point d'entrée public ─────────────────────────────────────────────────────

@st.fragment
def render(df: pd.DataFrame, df_hist: pd.DataFrame, df_positions: pd.DataFrame):
    auto_tickers = sorted(
        df[df["categorie"].isin(CATEGORIES_AUTO) & (df["ticker"] != "")]["ticker"]
        .dropna().unique().tolist()
    )

    has_history = not df_hist.empty or (not df_positions.empty and bool(auto_tickers))

    if not has_history:
        return

    st.subheader("Évolution", anchor=False)

    # ── Traitement des données avant création des widgets ───────────────────────────────
    default_period = PERIOD_DEFAULT
    yf_period, nb_jours = PERIOD_OPTIONS[default_period]
    
    start_date = None
    if nb_jours is not None:
        start_date = pd.Timestamp.today().normalize() - pd.Timedelta(days=nb_jours)

    with st.spinner("Reconstruction de l'historique…"):
        df_prices = fetch_historical_prices(tuple(auto_tickers), yf_period) if auto_tickers else pd.DataFrame()
        cat_evo = build_category_evolution(df, df_hist, df_positions, df_prices, tuple(CATEGORIES_AUTO))

    # ── Sélecteurs période + catégorie + benchmark ───────────────────────────────────────
    col_left, col_right = st.columns([0.8, 0.2])
    
    with col_left:
        with st.container(horizontal=True):
            period_label = st.radio(
                "Période",
                options=list(PERIOD_OPTIONS.keys()),
                index=list(PERIOD_OPTIONS.keys()).index(PERIOD_DEFAULT),
                horizontal=True,
                key="period_selector",
            )
    
            CATEGORIES_EXCLUES_GRAPHE = {"Immobilier"}
            options_cat = [c for c in cat_evo.columns if c not in CATEGORIES_EXCLUES_GRAPHE] if not cat_evo.empty else []

            selected_cats = st.segmented_control(
                "Catégories",
                options=options_cat,
                selection_mode="multi",
                key="cat_selector",
            )
 
    with col_right:
        benchmark_label = st.selectbox(
            "Comparer avec",
            options=list(BENCHMARK_OPTIONS.keys()),
            index=0,
            key="benchmark_selector",
            help="Comparer avec un indice de référence en pourcentage de variation"
        )

    # Si la période a changé, retraiter les données
    if period_label != default_period:
        yf_period, nb_jours = PERIOD_OPTIONS[period_label]
        
        start_date = None
        if nb_jours is not None:
            start_date = pd.Timestamp.today().normalize() - pd.Timedelta(days=nb_jours)

        with st.spinner("Reconstruction de l'historique…"):
            df_prices = fetch_historical_prices(tuple(auto_tickers), yf_period) if auto_tickers else pd.DataFrame()
            cat_evo = build_category_evolution(df, df_hist, df_positions, df_prices, tuple(CATEGORIES_AUTO))

    benchmark_ticker = BENCHMARK_OPTIONS[benchmark_label]

    # Récupérer les données du benchmark
    df_benchmark = pd.DataFrame()
    if benchmark_ticker:
        df_benchmark = fetch_historical_prices((benchmark_ticker,), yf_period)

    # Filtrage par période
    if start_date is not None:
        if not cat_evo.empty:
            cat_evo = cat_evo[cat_evo.index >= start_date]
        if not df_benchmark.empty:
            df_benchmark = df_benchmark[df_benchmark.index >= start_date]

    # Aucune sélection = toutes les catégories
    active_cats = selected_cats if selected_cats else options_cat

    _render_chart(active_cats, cat_evo, df_benchmark, benchmark_ticker, benchmark_label, df, df_positions, start_date)


def _render_chart(
    active_cats: list[str],
    cat_evo: pd.DataFrame,
    df_benchmark: pd.DataFrame,
    benchmark_ticker: str | None,
    benchmark_label: str,
    df: pd.DataFrame,
    df_positions: pd.DataFrame,
    start_date: pd.Timestamp | None,
):
    fig = go.Figure()

    has_benchmark = (
        benchmark_ticker
        and not df_benchmark.empty
        and benchmark_ticker in df_benchmark.columns
        and active_cats
        and not cat_evo.empty
    )

    # ── Métriques de performance ─────────────────────────────────────────────
    portfolio_pct = None
    bench_pct = None
    
    if has_benchmark:
        cols_actives = [c for c in active_cats if c in cat_evo.columns]
        active_total = cat_evo[cols_actives].sum(axis=1)

        bench_series = df_benchmark[benchmark_ticker].dropna()
        first_date = active_total.index[0]
        bench_series = bench_series[bench_series.index >= first_date]

        if not bench_series.empty and float(active_total.iloc[0]) > 0 and float(bench_series.iloc[0]) > 0:
            portfolio_pct = (active_total / float(active_total.iloc[0]) - 1) * 100
            
            # Calculer un benchmark ajusté qui tient compte des changements de quantité
            # On utilise les mêmes positions que le portfolio pour le benchmark
            df_assets = pd.DataFrame([{
                "id": "bench_temp",
                "nom": benchmark_label,
                "categorie": "Crypto",
                "ticker": benchmark_ticker
            }])
            
            # Créer un DataFrame de positions pour le benchmark avec les mêmes quantités que le portfolio crypto
            df_positions_bench = df_positions[df_positions["asset_id"].isin(
                df[df["categorie"] == "Crypto"]["id"]
            )].copy()
            if not df_positions_bench.empty:
                df_positions_bench["asset_id"] = "bench_temp"
                
                # Calculer l'évolution du benchmark avec les mêmes quantités
                raw_bench = _compute_raw_evolution(
                    df_assets, pd.DataFrame(), df_positions_bench, 
                    pd.DataFrame({benchmark_ticker: bench_series}), 
                    ("Crypto",)
                )
                
                if not raw_bench.empty:
                    bench_evo = raw_bench.groupby("date")["valeur"].sum()
                    bench_evo = bench_evo[bench_evo.index >= first_date]
                    if not bench_evo.empty:
                        bench_pct = (bench_evo / float(bench_evo.iloc[0]) - 1) * 100
                    else:
                        bench_pct = (bench_series / float(bench_series.iloc[0]) - 1) * 100
                else:
                    bench_pct = (bench_series / float(bench_series.iloc[0]) - 1) * 100
            else:
                bench_pct = (bench_series / float(bench_series.iloc[0]) - 1) * 100

            # stocker les métriques de performance pour la légende
            portfolio_final = portfolio_pct.iloc[-1] if not portfolio_pct.empty else 0
            bench_final = bench_pct.iloc[-1] if not bench_pct.empty else 0
            
    if has_benchmark and portfolio_pct is not None and bench_pct is not None:
        # ── Mode comparaison : deux courbes en % de variation ─────────────────
        portfolio_color = CATEGORY_COLOR_MAP.get(active_cats[0], "#6366F1") if active_cats else "#6366F1"

        fig.add_trace(go.Scatter(
            x=portfolio_pct.index,
            y=portfolio_pct.values,
            mode="lines",
            name="Mon portfolio" + f" {portfolio_final:+.1f}%",
            line=dict(color=portfolio_color, width=2),
        ))
        fig.add_trace(go.Scatter(
            x=bench_pct.index,
            y=bench_pct.values,
            mode="lines",
            name=benchmark_label + " : "+ f"{bench_final:+.1f}%",
            line=dict(color=BENCHMARK_COLOR, width=2, dash="dot"),
        ))

        fig.update_layout(
            **PLOTLY_LAYOUT,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                        bgcolor="rgba(0,0,0,0)", font=dict(color="#E8EAF0", size=12)),
        )
        fig.add_hline(y=0, line_color="#4B5563", line_width=1)
        fig.update_yaxes(ticksuffix=" %", tickformat=".1f")

    else:
        # ── Mode normal : aires empilées en € ─────────────────────────────────
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

        fig.update_layout(
            **PLOTLY_LAYOUT,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                        bgcolor="rgba(0,0,0,0)", font=dict(color="#E8EAF0", size=12)),
        )
        fig.update_yaxes(ticksuffix=" €", tickformat=",.0f")

    st.plotly_chart(fig, width="stretch", config={"staticPlot": True})