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
from services.assets import compute_by_category, compute_total
from services.db import get_total_emprunts, load_emprunts
from constants import CATEGORY_COLOR_MAP, CATEGORIES_AUTO, PLOTLY_LAYOUT


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


# ── Répartition actifs par catégorie (cartes) ────────────────────────────────

def _render_repartition_actifs(df: pd.DataFrame):
    stats = compute_by_category(df)
    if stats.empty:
        return

    st.subheader("Actifs par catégorie", anchor=False)

    # Calcul du PnL par catégorie (uniquement pour les catégories auto)
    pnl_by_cat: dict[str, float] = {}
    for categorie in CATEGORIES_AUTO:
        df_cat = df[df["categorie"] == categorie]
        if df_cat.empty:
            continue
        valeur_actuelle = df_cat["montant"].sum()
        valeur_achat = (df_cat["pru"] * df_cat["quantite"]).sum()
        if valeur_achat > 0:
            pnl_by_cat[categorie] = valeur_actuelle - valeur_achat

    # En-tête de la liste
    header_cols = st.columns([3, 1.5, 2, 2])
    header_cols[0].caption("Catégorie")
    header_cols[1].caption("Répartition")
    header_cols[2].caption("Valeur")
    header_cols[3].caption("Plus/moins-value")

    for _, row in stats.iterrows():
        categorie = row["categorie"]
        color = CATEGORY_COLOR_MAP.get(categorie, "#CCCCCC")
        pnl = pnl_by_cat.get(categorie)

        with st.container(border=True):
            cols = st.columns([3, 1.5, 2, 2])

            # Nom coloré
            cols[0].markdown(
                f"<span style='color:{color}; font-size:0.85em;'>●</span> "
                f"<span style='color:{color}; font-size:0.85em; text-transform:uppercase; "
                f"letter-spacing:0.08em;'>{categorie}</span>",
                unsafe_allow_html=True,
            )

            # Répartition %
            cols[1].write(f"{row['pourcentage']:.1f} %")

            # Valeur
            cols[2].write(f"{row['montant']:,.2f} €")

            # PnL (uniquement si disponible)
            if pnl is not None:
                sign = "+" if pnl >= 0 else ""
                badge_color = "green" if pnl >= 0 else "red"
                icon = ":material/trending_up:" if pnl >= 0 else ":material/trending_down:"
                cols[3].markdown(f":{badge_color}-badge[{icon} {sign}{pnl:,.2f} €]")
            else:
                cols[3].caption("—")


# ── Répartition par enveloppe fiscale ────────────────────────────────────────

def _render_enveloppes(df: pd.DataFrame):
    df_env = df[df["enveloppe"].notna() & (df["enveloppe"].str.strip() != "")]
    if df_env.empty:
        return

    totaux = (
        df_env.groupby("enveloppe")["montant"]
        .sum()
        .sort_values(ascending=False)
    )

    st.subheader("Actifs par enveloppe", anchor=False)
    with st.container(horizontal=True):
        for enveloppe, montant in totaux.items():
            st.metric(label=enveloppe, value=f"{montant:,.2f} €", border=True)


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

    st.divider()
    _render_enveloppes(df)

    df_emprunts = load_emprunts()
    if not df_emprunts.empty:
        st.divider()
        _render_passifs(df_emprunts)