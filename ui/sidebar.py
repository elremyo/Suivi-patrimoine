"""
ui/sidebar.py
──────────────
Contenu de la sidebar : téléchargement des données, réinitialisation.

Point d'entrée unique : render(df, invalidate_cache_fn, flash_fn)
"""

import streamlit as st
import pandas as pd
from services.storage import (
    download_assets, download_historique, download_positions,
    reset_all_data,
)

def render(df: pd.DataFrame, invalidate_cache_fn, flash_fn):
    with st.sidebar:
        # ── Téléchargement (visible uniquement si des données existent) ───────
        if not df.empty:
            st.subheader("Télécharger mes données", anchor=False)
            st.download_button(
                "Liste des actifs",
                data=download_assets(df),
                file_name="sauvegarde_actifs.csv",
                mime="text/csv",
                icon=":material/download:",
                use_container_width=True,
                key="btn_dl_assets",
                help="Nom, catégorie, montant, ticker… de tous tes actifs.",
            )
            st.download_button(
                "Historique des montants",
                data=download_historique(),
                file_name="sauvegarde_historique.csv",
                mime="text/csv",
                icon=":material/download:",
                use_container_width=True,
                key="btn_dl_historique",
                help="Évolution des montants dans le temps (actifs manuels).",
            )
            st.download_button(
                "Historique des positions",
                data=download_positions(),
                file_name="sauvegarde_positions.csv",
                mime="text/csv",
                icon=":material/download:",
                use_container_width=True,
                key="btn_dl_positions",
                help="Évolution des quantités dans le temps (actions, cryptos).",
            )

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
                