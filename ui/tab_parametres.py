"""
ui/tab_parametres.py
─────────────────────
Contenu du tab "⚙️ Paramètres" : gestion du référentiel courtiers et enveloppes.

Point d'entrée unique : render(df, invalidate_cache_fn)
"""

import streamlit as st
import pandas as pd
from services.referentiel import (
    get_courtiers,
    add_courtier,
    delete_courtier,
    rename_courtier
)


def _render_liste(
    label: str,
    items: list[str],
    add_fn,
    delete_fn,
    df_assets: pd.DataFrame,
    add_key: str,
    col_name: str,
    placeholder: str,
    invalidate_cache_fn=None,
):
    """
    Composant générique : affiche une liste avec ajout, suppression,
    et renommage optionnel.
    """
    st.subheader(label, anchor=False)

    # ── Ajout ──────────────────────────────────────────────────────────────
    col_input, col_button = st.columns([10, 2], vertical_alignment="center")
    with col_input:
        nouveau = st.text_input(
            label,
            placeholder=placeholder,
            label_visibility="collapsed",
            key=f"input_{add_key}",
        )
    with col_button:
        if st.button("Ajouter", key=f"btn_add_{add_key}", type="primary", width="stretch"):
            if nouveau.strip():
                ok, msg = add_fn(nouveau.strip())
                st.toast(msg, icon="✅" if ok else "⚠️")
                if ok:
                    st.rerun()
            else:
                st.toast("Le champ ne peut pas être vide.", icon="⚠️")

    # ── Liste ──────────────────────────────────────────────────────────────
    if not items:
        st.caption("Aucun élément pour l'instant.")
        return

    editing_key  = f"_editing_{add_key}"
    deleting_key = f"_deleting_{add_key}"
    editing  = st.session_state.get(editing_key)
    deleting = st.session_state.get(deleting_key)

    for item in items:
        with st.container(border=True):
            is_used = (
                not df_assets.empty
                and (df_assets[col_name].astype(str).str.strip() == item).any()
            )

            if editing == item:
                # ── Mode édition inline ────────────────────────────────────────
                c1, c2, c3 = st.columns([10, 0.9, 0.9], vertical_alignment="center")
                nouveau_nom = c1.text_input(
                    "Renommer",
                    value=item,
                    label_visibility="collapsed",
                    key=f"rename_input_{add_key}_{item}",
                )
                if c2.button("", icon=":material/check:", key=f"confirm_rename_{add_key}_{item}", help="Confirmer", type="primary"):
                    ok, msg, df_assets = rename_courtier(item, nouveau_nom, df_assets)
                    st.toast(msg, icon="✅" if ok else "⚠️")
                    st.session_state.pop(editing_key, None)
                    if ok:
                        if invalidate_cache_fn:
                            invalidate_cache_fn()
                        st.rerun()
                if c3.button("", icon=":material/close:", key=f"cancel_rename_{add_key}_{item}", help="Annuler"):
                    st.session_state.pop(editing_key, None)
                    st.rerun()

            elif deleting == item:
                # ── Mode confirmation de suppression ───────────────────────────
                with st.container(border=True):
                    st.warning(f"Supprimer **{item}** ? Cette action est irréversible.", icon=":material/warning:")
                    c1, c2 = st.columns(2)
                    if c1.button("Annuler", use_container_width=True, key=f"cancel_del_{add_key}_{item}"):
                        st.session_state.pop(deleting_key, None)
                        st.rerun()
                    if c2.button("Confirmer", type="primary", use_container_width=True, key=f"confirm_del_{add_key}_{item}"):
                        ok, msg = delete_fn(item, df_assets)
                        st.toast(msg, icon="✅" if ok else "⚠️")
                        st.session_state.pop(deleting_key, None)
                        if ok:
                            st.rerun()

            else:
                # ── Mode affichage normal ──────────────────────────────────────
                nb_cols = [10, 0.9, 0.9]
                cols = st.columns(nb_cols, vertical_alignment="center")
                cols[0].write(item)

                if cols[1].button("", icon=":material/edit:", key=f"edit_{add_key}_{item}", help=f"Renommer « {item} »"):
                    st.session_state[editing_key] = item
                    st.rerun()
                delete_col = cols[2]


                if is_used:
                    delete_col.button("", icon=":material/delete:", disabled=True, key=f"del_{add_key}_{item}", help=f"Impossible : **{item}** est utilisé par un actif.")
                else:
                    if delete_col.button("", icon=":material/delete:", key=f"del_{add_key}_{item}", help=f"Supprimer **{item}**"):
                        st.session_state[deleting_key] = item
                        st.rerun()


# ── Point d'entrée public ─────────────────────────────────────────────────────

def render(df: pd.DataFrame, invalidate_cache_fn=None):
    st.subheader("Mes courtiers", anchor=False)

    _render_liste(
        label="",
        items=get_courtiers(),
        add_fn=add_courtier,
        delete_fn=delete_courtier,
        df_assets=df,
        add_key="courtier",
        col_name="courtier",
        placeholder="Nouveau courtier…",
        invalidate_cache_fn=invalidate_cache_fn,
    )
