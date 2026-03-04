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


# ── Point d'entrée public ─────────────────────────────────────────────────────

def render(df: pd.DataFrame):
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
            btn_key_prefix="courtier",
            placeholder="Nouveau courtier…",
        )

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