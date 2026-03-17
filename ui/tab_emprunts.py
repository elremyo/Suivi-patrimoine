"""
ui/tab_emprunts.py
──────────────────
Onglet Passifs : liste des emprunts, ajout / modification / suppression (modales).
"""

import streamlit as st
import pandas as pd

from services.db_emprunts import load_emprunts, get_total_emprunts
from ui.emprunt_form import set_emprunt_dialog_create, set_emprunt_dialog_edit, set_emprunt_dialog_delete


def _render_emprunt_row(row: pd.Series):
    cols = st.columns([4, 2, 1.5, 2, 2, 1.5, 0.5, 0.5])

    # Nom
    cols[0].write(row["nom"])
    date_debut = row.get("date_debut")
    if date_debut is not None and not (isinstance(date_debut, float) and pd.isna(date_debut)):
        cols[0].caption(f"Depuis {pd.Timestamp(date_debut).strftime('%b %Y')} · {row['duree_mois']} mois")

    # Montant emprunté
    cols[1].write(f"{row['montant_emprunte']:,.0f} €")

    # Taux
    cols[2].write(f"{row['taux_annuel']:.2f} %")

    # Mensualité
    cols[3].write(f"{row['mensualite']:,.0f} €")

    # Capital restant dû
    crd = row.get("capital_restant_du")
    if crd is not None and not (isinstance(crd, float) and pd.isna(crd)):
        cols[4].write(f"{crd:,.0f} €")
    else:
        cols[4].caption("—")

    # % remboursé
    montant_emprunte = float(row["montant_emprunte"])
    if crd is not None and not (isinstance(crd, float) and pd.isna(crd)) and montant_emprunte > 0:
        pct_rembourse = (montant_emprunte - float(crd)) / montant_emprunte * 100
        cols[5].write(f"{pct_rembourse:.0f} %")
    else:
        cols[5].caption("—")

    # Actions
    if cols[6].button("", key=f"emprunt_edit_{row['id']}", icon=":material/edit_square:", help="Modifier"):
        set_emprunt_dialog_edit(row["id"])
        st.rerun()
    if cols[7].button("", key=f"emprunt_del_{row['id']}", icon=":material/delete:", help="Supprimer"):
        set_emprunt_dialog_delete(row["id"])
        st.rerun()

    # Détail coût total sous la ligne principale
    interets_totaux = row["mensualite"] * row["duree_mois"] - montant_emprunte # Ne prend pas en compte le taux d'intérêt car il est déjà inclus dans la mensualité
    cout_total = montant_emprunte + interets_totaux
    st.caption(
        f"Emprunté {montant_emprunte:,.0f} € · "
        f"Intérêts {interets_totaux:,.0f} € · "
        f"Coût total {cout_total:,.0f} €"
    )


def render(flash_fn) -> None:
    df = load_emprunts()
    total_crd = get_total_emprunts()

    # ── Métrique + bouton sur la même ligne ───────────────────────────────────
    st.metric(label="Total capital restant dû", value=f"{total_crd:,.2f} €")
    with st.container(horizontal=True, vertical_alignment="center"):
        st.write("")
        if st.button("Ajouter un emprunt", type="primary", key="btn_add_emprunt", icon=":material/add:"):
            set_emprunt_dialog_create()
            st.rerun()

    st.space(size="small")

    if df.empty:
        st.info("Aucun emprunt pour l'instant. Ajoute un prêt immobilier, un crédit conso, etc.")
        return

    # ── En-tête des colonnes ──────────────────────────────────────────────────
    header_cols = st.columns([4, 2, 1.5, 2, 2, 1.5, 0.5, 0.5])
    header_cols[0].empty()
    header_cols[1].caption("Montant emprunté")
    header_cols[2].caption("Taux")
    header_cols[3].caption("Mensualité")
    header_cols[4].caption("Restant dû")
    header_cols[5].caption("Remboursé")

    # ── Liste des emprunts ────────────────────────────────────────────────────
    for _, row in df.iterrows():
        with st.container(border=True, vertical_alignment="center"):
            _render_emprunt_row(row)