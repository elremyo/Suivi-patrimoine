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
from services.db import get_total_emprunts, load_emprunts, load_contrats
from constants import CATEGORY_COLOR_MAP, CATEGORIES_AUTO, PLOTLY_LAYOUT
from ui.asset_form import set_dialog_create


# ── Métriques clés ────────────────────────────────────────────────────────────

def _render_kpis(df: pd.DataFrame):
    total_actifs = compute_total(df) if not df.empty else 0.0
    total_passifs = get_total_emprunts()
    patrimoine_net = total_actifs - total_passifs

    col_total, col_passifs, col_net = st.columns(3)
    col_total.metric(label="Patrimoine brut", value=f"{total_actifs:,.2f} €")
    col_passifs.metric(label="Total passifs (emprunts)", value=f"{total_passifs:,.2f} €")
    col_net.metric(label="Patrimoine net", value=f"{patrimoine_net:,.2f} €")


# ── Répartition actifs par catégorie (cartes) ────────────────────────────────

def _render_repartition_actifs(df: pd.DataFrame):
    stats = compute_by_category(df)
    if stats.empty:
        return

    st.subheader("Actifs", anchor=False)

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
    header_cols = st.columns([5, 1, 1, 1])
    header_cols[0].empty()
    header_cols[1].caption("Répartition")
    header_cols[2].caption("Valeur")
    header_cols[3].caption("Plus/moins-value")

    for _, row in stats.iterrows():
        categorie = row["categorie"]
        color = CATEGORY_COLOR_MAP.get(categorie, "#CCCCCC")
        pnl = pnl_by_cat.get(categorie)

        with st.container(border=True):
            cols = st.columns([5, 1, 1, 1])

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
                # Calcul du pourcentage
                df_cat = df[df["categorie"] == categorie]
                valeur_achat = (df_cat["pru"] * df_cat["quantite"]).sum()
                pourcentage = (pnl / valeur_achat * 100) if valeur_achat > 0 else 0.0
                
                sign = "+" if pnl >= 0 else ""
                sign_pct = "+" if pourcentage >= 0 else ""
                badge_color = "green" if pnl >= 0 else "red"
                icon = ":material/trending_up:" if pnl >= 0 else ":material/trending_down:"
                cols[3].markdown(f":{badge_color}-badge[{icon} {sign}{pnl:,.2f} € ({sign_pct}{pourcentage:.1f}%)]")
            else:
                cols[3].caption("—")


# ── Répartition par contrat ───────────────────────────────────────────

def _render_contrats(df: pd.DataFrame):
    df_contrats_assets = df[df["contrat_id"].notna() & (df["contrat_id"].str.strip() != "")]
    if df_contrats_assets.empty:
        return

    # Récupérer les informations des contrats
    try:
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
        
        st.subheader("Actifs par contrat", anchor=False)
        with st.container(horizontal=True):
            for contrat, montant in totaux.items():
                st.metric(label=contrat, value=f"{montant:,.2f} €", border=True)
                
    except Exception as e:
        st.subheader("Actifs par contrat", anchor=False)
        st.caption("Impossible d'afficher les contrats")


# ── Résumé des passifs ────────────────────────────────────────────────────────

def _render_passifs(df_emprunts: pd.DataFrame, total_actifs: float):
    if df_emprunts.empty:
        return

    st.subheader("Passifs", anchor=False)

    cols_entete = st.columns([5, 1, 1, 1])
    cols_entete[1].caption("Part du patrimoine")
    cols_entete[2].caption("Emprunté")
    cols_entete[3].caption("Restant dû")

    for _, row in df_emprunts.iterrows():
        crd = row.get("capital_restant_du")
        crd_str = f"{crd:,.0f} €" if crd is not None and not pd.isna(crd) else "—"
        pct = (crd / total_actifs * 100) if (total_actifs > 0 and crd is not None and not pd.isna(crd)) else None
        pct_str = f"{pct:.1f} %" if pct is not None else "—"

        with st.container(border=True):
            cols = st.columns([5, 1, 1, 1])
            cols[0].markdown(f"**{row['nom']}**")
            cols[1].write(pct_str)
            cols[2].write(f"{row['montant_emprunte']:,.0f} €")
            cols[3].write(crd_str)


# ── Point d'entrée public ─────────────────────────────────────────────────────

def render(df: pd.DataFrame):
    total_actifs = compute_total(df) if not df.empty else 0.0

    _render_kpis(df)

    if df.empty:
        with st.container(border=True):
            st.markdown("### Bienvenue sur ton suivi de patrimoine 👋")
            st.markdown(" ")
            st.markdown("**1. Ajoute tes actifs**")
            st.caption("Livrets, immobilier, actions, crypto, fonds euros — tous tes placements au même endroit.")
            st.markdown("**2. Les prix se mettent à jour automatiquement**")
            st.caption("Pour tes actions et cryptos, l'app récupère les cours en temps réel via Yahoo Finance.")
            st.markdown("**3. Suis l'évolution de ton patrimoine**")
            st.caption("Visualise la répartition de tes actifs et leur évolution dans le temps.")
            if st.button("+ Ajouter mon premier actif", type="primary", use_container_width=True, key="btn_empty_state"):
                set_dialog_create()
                st.rerun()

    _render_repartition_actifs(df)

    df_emprunts = load_emprunts()
    if not df_emprunts.empty:
        st.divider()
        _render_passifs(df_emprunts, total_actifs)

    st.divider()
    _render_contrats(df)