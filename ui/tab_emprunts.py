"""
ui/tab_emprunts.py
──────────────────
Onglet Emprunts : liste des prêts, ajout / modification / suppression (modales).
"""

import streamlit as st
import pandas as pd

from services.db import load_emprunts, delete_emprunt, get_total_emprunts
from ui.emprunt_form import set_emprunt_dialog_create, set_emprunt_dialog_edit, set_emprunt_dialog_delete


def render(flash_fn) -> None:
    df = load_emprunts()
    total_crd = get_total_emprunts()

    st.metric(label="Total capital restant dû", value=f"{total_crd:,.2f} €")
    st.space(size="small")

    if st.button("+ Ajouter un emprunt", type="primary", key="btn_add_emprunt"):
        set_emprunt_dialog_create()
        st.rerun()

    st.space(size="small")

    if df.empty:
        st.caption("Aucun emprunt pour l'instant. Ajoute un prêt immobilier, un crédit conso, etc.")
        return

    for _, row in df.iterrows():
        with st.container(border=True):
            cols = st.columns([3, 1.5, 1.2, 1.2, 1.2, 0.6, 0.6])
            cols[0].markdown(f"**{row['nom']}**")
            cols[1].caption("Emprunté")
            cols[1].write(f"{row['montant_emprunte']:,.0f} €")
            cols[2].caption("Taux")
            cols[2].write(f"{row['taux_annuel']:.2f} %")
            cols[3].caption("Mensualité")
            cols[3].write(f"{row['mensualite']:,.0f} €")
            cols[4].caption("Restant dû")
            crd = row.get("capital_restant_du")
            if crd is not None and not pd.isna(crd):
                cols[4].write(f"{crd:,.0f} €")
            else:
                cols[4].caption("—")
            if cols[5].button("", key=f"emprunt_edit_{row['id']}", icon=":material/edit_square:", help="Modifier"):
                set_emprunt_dialog_edit(row["id"])
                st.rerun()
            if cols[6].button("", key=f"emprunt_del_{row['id']}", icon=":material/delete:", help="Supprimer"):
                set_emprunt_dialog_delete(row["id"])
                st.rerun()
