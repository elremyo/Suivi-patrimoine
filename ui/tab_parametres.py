"""
ui/tab_parametres.py
─────────────────────
Contenu du tab "⚙️ Paramètres" : gestion du référentiel courtiers et enveloppes.

Point d'entrée unique : render(df, invalidate_cache_fn)
"""

import streamlit as st
import pandas as pd
from services.referentiel import (
    get_courtiers, get_enveloppes,
    add_courtier, add_enveloppe,
    delete_courtier, delete_enveloppe,
    rename_courtier,
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
    rename_fn=None,
    invalidate_cache_fn=None,
):
    """
    Composant générique : affiche une liste avec ajout, suppression,
    et renommage optionnel (si rename_fn est fourni).
    """
    st.subheader(label, anchor=False)

    # ── Ajout ──────────────────────────────────────────────────────────────
    with st.container(horizontal=True, vertical_alignment="bottom"):
        nouveau = st.text_input(
            label,
            placeholder=placeholder,
            label_visibility="collapsed",
            key=f"input_{add_key}",
        )
        if st.button("Ajouter", key=f"btn_add_{add_key}", type="primary"):
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
        is_used = (
            not df_assets.empty
            and (df_assets[col_name].astype(str).str.strip() == item).any()
        )

        if rename_fn and editing == item:
            # ── Mode édition inline ────────────────────────────────────────
            c1, c2, c3 = st.columns([6, 1, 1], vertical_alignment="center")
            nouveau_nom = c1.text_input(
                "Renommer",
                value=item,
                label_visibility="collapsed",
                key=f"rename_input_{add_key}_{item}",
            )
            if c2.button("", icon=":material/check:", key=f"confirm_rename_{add_key}_{item}", help="Confirmer", type="primary"):
                ok, msg, df_assets = rename_fn(item, nouveau_nom, df_assets)
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
                st.warning(f"Supprimer « {item} » ? Cette action est irréversible.", icon=":material/warning:")
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
            nb_cols = [6, 1, 1] if rename_fn else [7, 1]
            cols = st.columns(nb_cols, vertical_alignment="center")
            cols[0].write(item)

            if rename_fn:
                if cols[1].button("", icon=":material/edit:", key=f"edit_{add_key}_{item}", help=f"Renommer « {item} »"):
                    st.session_state[editing_key] = item
                    st.rerun()
                delete_col = cols[2]
            else:
                delete_col = cols[1]

            if is_used:
                delete_col.button("", icon=":material/delete:", disabled=True, key=f"del_{add_key}_{item}", help=f"Impossible — « {item} » est utilisé par un actif.")
            else:
                if delete_col.button("", icon=":material/delete:", key=f"del_{add_key}_{item}", help=f"Supprimer « {item} »"):
                    st.session_state[deleting_key] = item
                    st.rerun()


# ── Point d'entrée public ─────────────────────────────────────────────────────

def render(df: pd.DataFrame, invalidate_cache_fn=None):
    st.subheader("Référentiel", anchor=False)
    st.caption("Gérez les courtiers et enveloppes proposés lors de la saisie d'un actif. "
               "L'icône :material/link: indique qu'un élément est utilisé par un actif — supprimez d'abord l'actif pour le retirer.")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        _render_liste(
            label="Courtiers",
            items=get_courtiers(),
            add_fn=add_courtier,
            delete_fn=delete_courtier,
            df_assets=df,
            add_key="courtier",
            col_name="courtier",
            placeholder="Nouveau courtier…",
            rename_fn=rename_courtier,
            invalidate_cache_fn=invalidate_cache_fn,
        )

    with col2:
        _render_liste(
            label="Enveloppes",
            items=get_enveloppes(),
            add_fn=add_enveloppe,
            delete_fn=delete_enveloppe,
            df_assets=df,
            add_key="enveloppe",
            col_name="enveloppe",
            placeholder="Nouvelle enveloppe…",
        )