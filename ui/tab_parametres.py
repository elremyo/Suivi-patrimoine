"""
ui/tab_parametres.py
─────────────────────
Contenu du tab "⚙️ Paramètres" : gestion des contrats.

Point d'entrée unique : render(df, invalidate_cache_fn)
"""

import streamlit as st
import pandas as pd
from services.db import load_contrats, add_contrat, update_contrat, delete_contrat


def _render_contrats(df_assets: pd.DataFrame, invalidate_cache_fn=None):
    """Interface de gestion des contrats (établissement + enveloppe)."""
    st.subheader("Mes contrats", anchor=False)
    st.caption("Un contrat combine un établissement (ex: Boursorama) avec une enveloppe (ex: PEA).")
    
    # ── Ajout d'un nouveau contrat ───────────────────────────────────────────
    with st.expander("Ajouter un contrat", expanded=False, icon=":material/add:"):
        col1, col2, col3 = st.columns([4, 4, 1.5], vertical_alignment="bottom")
        with col1:
            etablissement = st.text_input(
                "Établissement *",
                placeholder="ex. Boursorama, Degiro, Crédit Agricole",
                key="new_contrat_etablissement"
            ).strip()
        with col2:
            from constants import ENVELOPPES
            enveloppe = st.selectbox(
                "Enveloppe *",
                options=sorted(ENVELOPPES),
                key="new_contrat_enveloppe"
            )
        with col3:
            if st.button("Créer le contrat", type="primary", key="btn_add_contrat"):
                if etablissement and enveloppe:
                    ok, msg, contrat_id = add_contrat(etablissement, enveloppe)
                    st.toast(msg, icon="✅" if ok else "⚠️")
                    if ok:
                        st.rerun()
                else:
                    st.toast("L'établissement et l'enveloppe sont obligatoires.", icon="⚠️")
    
    # ── Liste des contrats existants ───────────────────────────────────────────
    df_contrats = load_contrats()
    
    if df_contrats.empty:
        st.caption("Aucun contrat pour l'instant.")
        return
    
    # Session state pour l'édition
    editing_key  = "_editing_contrat"
    deleting_key = "_deleting_contrat"
    editing  = st.session_state.get(editing_key)
    deleting = st.session_state.get(deleting_key)
    
    for _, row in df_contrats.iterrows():
        contrat_id = row['id']
        display_name = f"{row['etablissement']} — {row['enveloppe']}"
        
        # Vérifier si le contrat est utilisé par des actifs
        is_used = (
            not df_assets.empty
            and (df_assets['contrat_id'].astype(str) == contrat_id).any()
        )
        
        with st.container(border=True, vertical_alignment="center"):
            if editing == contrat_id:
                # ── Mode édition inline ────────────────────────────────────────
                with st.container(border=False, vertical_alignment="center"):
                    st.markdown("**Modifier le contrat**")
                    col1, col2, col3, col4 = st.columns([5, 5, 0.9, 0.9], vertical_alignment="bottom")
                    with col1:
                        new_etablissement = st.text_input(
                            "Établissement",
                            value=row['etablissement'],
                            key=f"edit_etablissement_{contrat_id}"
                        ).strip()
                    with col2:
                        new_enveloppe = st.selectbox(
                            "Enveloppe",
                            options=sorted(ENVELOPPES),
                            index=sorted(ENVELOPPES).index(row['enveloppe']),
                            key=f"edit_enveloppe_{contrat_id}"
                        )
                    with col3:
                        if st.button("", icon=":material/check:", key=f"confirm_edit_contrat_{contrat_id}", help="Confirmer", type="primary"):
                            if new_etablissement and new_enveloppe:
                                ok, msg = update_contrat(contrat_id, new_etablissement, new_enveloppe)
                                st.toast(msg, icon="✅" if ok else "⚠️")
                                st.session_state.pop(editing_key, None)
                                if ok:
                                    if invalidate_cache_fn:
                                        invalidate_cache_fn()
                                    st.rerun()
                            else:
                                st.toast("L'établissement et l'enveloppe sont obligatoires.", icon="⚠️")
                    with col4:
                        if st.button("", icon=":material/close:", key=f"cancel_edit_contrat_{contrat_id}", help="Annuler"):
                            st.session_state.pop(editing_key, None)
                            st.rerun()

            elif deleting == contrat_id:
                # ── Mode confirmation de suppression ───────────────────────────
                with st.container(border=True):
                    st.warning(f"Supprimer **{display_name}** ? Cette action est irréversible.", icon=":material/warning:")
                    c1, c2 = st.columns(2)
                    if c1.button("Annuler", use_container_width=True, key=f"cancel_del_contrat_{contrat_id}"):
                        st.session_state.pop(deleting_key, None)
                        st.rerun()
                    if c2.button("Confirmer", type="primary", disabled=is_used, use_container_width=True, key=f"confirm_del_contrat_{contrat_id}"):
                        ok, msg = delete_contrat(contrat_id)
                        st.toast(msg, icon="✅" if ok else "⚠️")
                        st.session_state.pop(deleting_key, None)
                        if ok:
                            st.rerun()

            else:
                # ── Mode affichage normal ──────────────────────────────────────
                cols = st.columns([10, 0.9, 0.9], vertical_alignment="center")
                cols[0].write(display_name)

                if cols[1].button("", icon=":material/edit:", key=f"edit_contrat_{contrat_id}", help=f"Modifier « {display_name} »"):
                    st.session_state[editing_key] = contrat_id
                    st.rerun()
                delete_col = cols[2]

                if is_used:
                    delete_col.button("", icon=":material/delete:", disabled=True, key=f"del_contrat_{contrat_id}", help=f"Impossible : **{display_name}** est utilisé par un actif.")
                else:
                    if delete_col.button("", icon=":material/delete:", key=f"del_contrat_{contrat_id}", help=f"Supprimer **{display_name} »"):
                        st.session_state[deleting_key] = contrat_id
                        st.rerun()




# ── Point d'entrée public ─────────────────────────────────────────────────────

def render(df: pd.DataFrame, invalidate_cache_fn=None):
    # ── Section Contrats ─────────────────────────────────────────────────────
    _render_contrats(df, invalidate_cache_fn)
