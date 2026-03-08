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


# Répartition par contrat

def _render_contrat_metrics(df: pd.DataFrame):
    if df.empty:
        return

    df_contrats_assets = df[df["contrat_id"].notna() & (df["contrat_id"].str.strip() != "")]
    if df_contrats_assets.empty:
        return

    # Récupérer les informations des contrats
    try:
        from services.db import load_contrats
        df_contrats = load_contrats()
        
        # Joindre les données
        df_merged = df_contrats_assets.merge(
            df_contrats, 
            left_on="contrat_id", 
            right_on="id", 
            how="left"
        )
        
        # Grouper par contrat (établissement + enveloppe)
        df_merged["contrat_display"] = df_merged["etablissement"] + " — " + df_merged["enveloppe"]
        
        totaux = (
            df_merged.groupby("contrat_display")["montant"]
            .sum()
            .sort_values(ascending=False)
        )
        
        st.subheader("Patrimoine par contrat", anchor=False)
        
        with st.container(horizontal=True):
            for contrat, montant in totaux.items():
                st.metric(label=contrat, value=f"{montant:,.2f} €", border=True)
                
    except Exception as e:
        st.subheader("Patrimoine par contrat", anchor=False)
        st.caption("Impossible d'afficher les contrats")


# ── Point d'entrée public ─────────────────────────────────────────────────────

def render(df: pd.DataFrame):
    if df.empty:
        st.info("Aucun actif enregistré. Ajoute des actifs pour voir la répartition.")
        return

    _render_pie_chart(df)
    _render_contrat_metrics(df)