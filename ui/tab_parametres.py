"""
ui/tab_parametres.py
─────────────────────
Contenu du tab "⚙️ Paramètres" : gestion du référentiel courtiers et enveloppes.

Point d'entrée unique : render(df)
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
    btn_key_prefix: str,
    placeholder: str,
):
    """Composant générique : affiche une liste avec ajout et suppression."""

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
                if ok:
                    st.toast(msg, icon="✅")
                    st.rerun()
                else:
                    st.toast(msg, icon="⚠️")
            else:
                st.toast("Le champ ne peut pas être vide.", icon="⚠️")

    # ── Liste ──────────────────────────────────────────────────────────────
    if not items:
        st.caption("Aucun élément pour l'instant.")
        return

    for item in items:
        # Est-ce que cet item est utilisé par un actif ?
        col_name = "courtier" if btn_key_prefix == "courtier" else "enveloppe"
        is_used = (
            not df_assets.empty
            and (df_assets[col_name].astype(str).str.strip() == item).any()
        )

        c1, c2 = st.columns([6, 1], vertical_alignment="center")
        c1.write(item)

        if is_used:
            # Icône discrète indiquant que l'item est en cours d'utilisation
            c2.caption(":grey[:material/link:]")
        else:
            if c2.button(
                "",
                key=f"del_{btn_key_prefix}_{item}",
                icon=":material/delete:",
                help=f"Supprimer « {item} »",
            ):
                ok, msg = delete_fn(item, df_assets)
                if ok:
                    st.toast(msg, icon="✅")
                    st.rerun()
                else:
                    st.toast(msg, icon="⚠️")


def _render_courtiers(df: pd.DataFrame):
    """Liste des courtiers avec ajout, renommage inline et suppression."""
    st.subheader("Courtiers", anchor=False)

    # ── Ajout ──────────────────────────────────────────────────────────────
    with st.container(horizontal=True, vertical_alignment="bottom"):
        nouveau = st.text_input(
            "Courtiers",
            placeholder="Nouveau courtier…",
            label_visibility="collapsed",
            key="input_courtier",
        )
        if st.button("Ajouter", key="btn_add_courtier", type="primary"):
            if nouveau.strip():
                ok, msg = add_courtier(nouveau.strip())
                st.toast(msg, icon="✅" if ok else "⚠️")
                if ok:
                    st.rerun()
            else:
                st.toast("Le champ ne peut pas être vide.", icon="⚠️")

    # ── Liste ──────────────────────────────────────────────────────────────
    items = get_courtiers()
    if not items:
        st.caption("Aucun courtier pour l'instant.")
        return

    editing = st.session_state.get("_editing_courtier")

    for item in items:
        is_used = (
            not df.empty
            and (df["courtier"].astype(str).str.strip() == item).any()
        )

        if editing == item:
            # Mode édition inline
            c1, c2, c3 = st.columns([5, 1, 1], vertical_alignment="center")
            nouveau_nom = c1.text_input(
                "Renommer",
                value=item,
                label_visibility="collapsed",
                key=f"rename_input_{item}",
            )
            if c2.button("", icon=":material/check:", key=f"confirm_rename_{item}", help="Confirmer"):
                ok, msg, df = rename_courtier(item, nouveau_nom, df)
                st.toast(msg, icon="✅" if ok else "⚠️")
                st.session_state.pop("_editing_courtier", None)
                if ok:
                    st.rerun()
            if c3.button("", icon=":material/close:", key=f"cancel_rename_{item}", help="Annuler"):
                st.session_state.pop("_editing_courtier", None)
                st.rerun()
        else:
            # Mode affichage normal
            c1, c2, c3 = st.columns([6, 1, 1], vertical_alignment="center")
            c1.write(item)
            if c2.button("", icon=":material/edit:", key=f"edit_courtier_{item}", help=f"Renommer « {item} »"):
                st.session_state["_editing_courtier"] = item
                st.rerun()
            if is_used:
                c3.caption(":grey[:material/link:]")
            else:
                if c3.button("", icon=":material/delete:", key=f"del_courtier_{item}", help=f"Supprimer « {item} »"):
                    ok, msg = delete_courtier(item, df)
                    st.toast(msg, icon="✅" if ok else "⚠️")
                    if ok:
                        st.rerun()


# ── Point d'entrée public ─────────────────────────────────────────────────────

def render(df: pd.DataFrame):
    st.subheader("Référentiel", anchor=False)
    st.caption("Gérez les courtiers et enveloppes proposés lors de la saisie d'un actif. "
               "L'icône :material/link: indique qu'un élément est utilisé par un actif — supprimez d'abord l'actif pour le retirer.")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        _render_courtiers(df)

    with col2:
        _render_liste(
            label="Enveloppes",
            items=get_enveloppes(),
            add_fn=add_enveloppe,
            delete_fn=delete_enveloppe,
            df_assets=df,
            add_key="enveloppe",
            btn_key_prefix="enveloppe",
            placeholder="Nouvelle enveloppe…",
        )