"""
ui/sidebar.py
──────────────
Contenu de la sidebar : mode démo, export/import des données, réinitialisation.

Point d'entrée unique : render(df, invalidate_cache_fn, flash_fn)
"""

import streamlit as st
import pandas as pd
from services.storage import (
    download_assets, download_historique, download_positions,
    import_assets, import_historique, import_positions,
)
from services.demo_mode import (
    is_demo_mode, has_personal_data,
    activate_demo, deactivate_demo, reset_all_data,
    DEMO_USER_NAME,
)

def render_demo_mode_section(invalidate_cache_fn, flash_fn):
    st.subheader("Mode démo", anchor=False)
    st.markdown(f":material/person: **{DEMO_USER_NAME}**")
    st.caption("Profil diversifié ~200 000 € \n\n Livrets · PEA · CTO · Crypto · Assurance vie · SCPI")
    demo_actif = is_demo_mode()
    nouveau_state = st.toggle(
        "Activer les données fictives",
        value=demo_actif,
        key="toggle_demo",
        help="Explore l'app avec des données fictives sur un an, sans saisir tes propres données.",
    )
    if nouveau_state != demo_actif:
        if nouveau_state:
            msg = activate_demo()
            st.session_state.pop("prices_refreshed", None)
        else:
            msg = deactivate_demo()
        flash_fn(msg, "success")
        st.cache_data.clear()
        invalidate_cache_fn()
        st.rerun()

def render(df: pd.DataFrame, invalidate_cache_fn, flash_fn):
    with st.sidebar:
        if df.empty or is_demo_mode() or not has_personal_data():
            with st.expander("Mode démo", expanded=True):
                render_demo_mode_section(invalidate_cache_fn, flash_fn)
        else:
            with st.expander("Mode démo"):
                render_demo_mode_section(invalidate_cache_fn, flash_fn)

        # ── Export & Import (visibles uniquement si des données existent) ─────
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

            st.subheader("Importer des données", anchor=False)
            st.caption(":orange[:material/warning: Remplace toutes les données existantes.]")

            f = st.file_uploader(
                "Actifs (.csv)",
                type="csv",
                key=f"up_assets_{st.session_state.get('_up_assets_v', 0)}",
            )
            if f:
                ok, msg = import_assets(f)
                flash_fn(msg, "success" if ok else "error")
                st.session_state["_up_assets_v"] = st.session_state.get("_up_assets_v", 0) + 1
                if ok:
                    invalidate_cache_fn()
                st.rerun()

            f = st.file_uploader(
                "Historique des montants (.csv)",
                type="csv",
                key=f"up_historique_{st.session_state.get('_up_historique_v', 0)}",
            )
            if f:
                ok, msg = import_historique(f)
                flash_fn(msg, "success" if ok else "error")
                st.session_state["_up_historique_v"] = st.session_state.get("_up_historique_v", 0) + 1
                if ok:
                    invalidate_cache_fn()
                st.rerun()

            f = st.file_uploader(
                "Historique des positions (.csv)",
                type="csv",
                key=f"up_positions_{st.session_state.get('_up_positions_v', 0)}",
            )
            if f:
                ok, msg = import_positions(f)
                flash_fn(msg, "success" if ok else "error")
                st.session_state["_up_positions_v"] = st.session_state.get("_up_positions_v", 0) + 1
                if ok:
                    invalidate_cache_fn()
                st.rerun()

        # ── Réinitialisation (visible uniquement si données perso) ────────────
        if not df.empty and not is_demo_mode():
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
                