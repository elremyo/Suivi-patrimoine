"""
ui/sidebar.py
──────────────
Contenu de la sidebar : téléchargement des données, réinitialisation.

Point d'entrée unique : render(df, invalidate_cache_fn, flash_fn)
"""

import streamlit as st
import pandas as pd
from services.db import reset_all_data

def render(df: pd.DataFrame, invalidate_cache_fn, flash_fn):
    with st.sidebar:
        # ── Réinitialisation (visible uniquement si données perso) ────────────
        if not df.empty:
            with st.expander("Supprimer mes données"):
                st.warning("Supprime définitivement toutes vos données. Irréversible !", icon=":material/warning:")

                confirm_input = st.text_input(
                    "Tape **SUPPRIMER** pour confirmer",
                    placeholder="SUPPRIMER",
                    key="reset_confirm_input",
                )
                if st.button(
                    "Tout supprimer",
                    icon=":material/delete_forever:",
                    type="primary",
                    disabled=confirm_input != "SUPPRIMER",
                    use_container_width=True,
                    key="btn_reset_all",
                ):
                    msg = reset_all_data()
                    flash_fn(msg, "success")
                    st.cache_data.clear()
                    invalidate_cache_fn()
                    st.rerun()
                