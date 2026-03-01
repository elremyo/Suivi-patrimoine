"""
ui/tab_repartition.py
──────────────────────
Point d'entrée unique : render(df)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from constants import CATEGORY_COLOR_MAP, PLOTLY_LAYOUT


# Répartition par catégorie 

def _render_pie_chart(df: pd.DataFrame):
    from services.assets import compute_by_category
    stats = compute_by_category(df)
    if stats.empty:
        return

    st.subheader("Répartition par catégorie", anchor=False)

    #affichage en metriques dans un contaioner horizontal
    with st.container(horizontal=True):
        for _, row in stats.iterrows():
            cat = row["categorie"]
            montant = row["montant"]
            st.metric(label=cat, value=f"{montant:,.2f} €", border=True,delta =f"{row['pourcentage']:.1f}%",delta_color="off",delta_arrow ="off")

    fig = go.Figure(go.Pie(
        labels=stats["categorie"],
        values=stats["montant"],
        marker=dict(colors=[CATEGORY_COLOR_MAP.get(cat, "#CCCCCC") for cat in stats["categorie"]]),
        textinfo="label+percent",
        textfont=dict(color="#E8EAF0", size=13),
        hole=0.35,
    ))
    fig.update_layout(
        **{**PLOTLY_LAYOUT, "margin": dict(l=10, r=10, t=10, b=10)},
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", config={"staticPlot": True})


# Répartition par catégorie enveloppe fiscale

def _render_enveloppe_metrics(df: pd.DataFrame):
    if df.empty:
        return

    df_env = df[df["enveloppe"].notna() & (df["enveloppe"].str.strip() != "")]
    if df_env.empty:
        return

    totaux = (
        df_env.groupby("enveloppe")["montant"]
        .sum()
        .sort_values(ascending=False)
    )

    st.subheader("Patrimoine par enveloppe", anchor=False)

    with st.container(horizontal=True):
        for enveloppe, montant in totaux.items():
            st.metric(label=enveloppe, value=f"{montant:,.2f} €", border=True)


# ── Point d'entrée public ─────────────────────────────────────────────────────

def render(df: pd.DataFrame):
    if df.empty:
        st.info("Aucun actif enregistré. Ajoutez des actifs pour voir la répartition.")
        return

    _render_pie_chart(df)
    _render_enveloppe_metrics(df)