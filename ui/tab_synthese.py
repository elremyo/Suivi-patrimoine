"""
ui/tab_synthese.py
───────────────────
Onglet principal "Synthèse" : vue globale du patrimoine.
- Métriques clés : total actifs / total passifs / patrimoine net
- Répartition des actifs par catégorie (métriques + camembert)
- Répartition par enveloppe fiscale
- Résumé des passifs (emprunts)

Point d'entrée unique : render(df)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from services.assets import compute_by_category, compute_total
from services.db import get_total_emprunts, load_emprunts
from constants import CATEGORY_COLOR_MAP, PLOTLY_LAYOUT


# ── Métriques clés ────────────────────────────────────────────────────────────

def _render_kpis(df: pd.DataFrame):
    total_actifs = compute_total(df) if not df.empty else 0.0
    total_passifs = get_total_emprunts()
    patrimoine_net = total_actifs - total_passifs

    col_total, col_passifs, col_net = st.columns(3)
    col_total.metric(label="Patrimoine brut (actifs)", value=f"{total_actifs:,.2f} €")
    col_passifs.metric(label="Total passifs (emprunts)", value=f"{total_passifs:,.2f} €")
    col_net.metric(
        label="Patrimoine net",
        value=f"{patrimoine_net:,.2f} €",
        delta=f"−{total_passifs:,.0f} € de dettes" if total_passifs > 0 else None,
        delta_color="inverse",
        delta_arrow="off",
    )


# ── Répartition actifs par catégorie ─────────────────────────────────────────

def _render_repartition_actifs(df: pd.DataFrame):
    stats = compute_by_category(df)
    if stats.empty:
        return

    st.subheader("Actifs par catégorie", anchor=False)

    with st.container(horizontal=True):
        for _, row in stats.iterrows():
            st.metric(
                label=row["categorie"],
                value=f"{row['montant']:,.2f} €",
                border=True,
                delta=f"{row['pourcentage']:.1f}%",
                delta_color="off",
                delta_arrow="off",
            )

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



# ── Résumé des passifs ────────────────────────────────────────────────────────

def _render_passifs(df_emprunts: pd.DataFrame):
    if df_emprunts.empty:
        return

    st.subheader("Passifs", anchor=False)

    for _, row in df_emprunts.iterrows():
        crd = row.get("capital_restant_du")
        crd_str = f"{crd:,.0f} €" if crd is not None and not pd.isna(crd) else "—"
        with st.container(border=True):
            cols = st.columns([4, 2, 2, 2])
            cols[0].markdown(f"**{row['nom']}**")
            cols[1].caption("Emprunté")
            cols[1].write(f"{row['montant_emprunte']:,.0f} €")
            cols[2].caption("Mensualité")
            cols[2].write(f"{row['mensualite']:,.0f} €")
            cols[3].caption("Restant dû")
            cols[3].write(crd_str)


# ── Point d'entrée public ─────────────────────────────────────────────────────

def render(df: pd.DataFrame):
    _render_kpis(df)

    if df.empty:
        st.info("Aucun actif enregistré. Ajoute des actifs pour voir la synthèse.")
        return

    st.divider()
    _render_repartition_actifs(df)


    df_emprunts = load_emprunts()
    if not df_emprunts.empty:
        st.divider()
        _render_passifs(df_emprunts)