"""
ui/tab_actifs.py
───────────────────
Contenu du tab "Actifs" : liste des actifs.
Les métriques globales (actifs / passifs / net) sont dans tab_synthese.py.
Les modales sont gérées via ui/asset_form.py.
Les téléchargements et la réinitialisation sont dans ui/sidebar.py.
"""

import streamlit as st
from constants import TYPE_BIEN_OPTIONS
import pandas as pd
from datetime import datetime
from services.asset_manager import refresh_prices
from ui.asset_form import set_dialog_create, set_dialog_edit, set_dialog_delete, set_dialog_update
from ui.asset_detail import set_asset_detail, is_asset_detail_active, get_current_asset_id
from constants import CATEGORIES_ASSETS, CATEGORIES_AUTO, CATEGORY_COLOR_MAP
from services.db_contrats import load_contrats
from services.db_emprunts import load_emprunts
from services.financial_calculations import calculate_rental_metrics, calculate_auto_asset_pnl


# ── Ligne d'actif ─────────────────────────────────────────────────────────────

def _render_asset_row(row: pd.Series, df_contrats: pd.DataFrame = None, df_emprunts: pd.DataFrame = None):    
    is_auto_row = row["categorie"] in CATEGORIES_AUTO
    cols = st.columns([4, 1, 1, 2, 0.5], vertical_alignment="center")

    # ── Colonne nom + infos discrètes ─────────────────────────────────────────
    contrat_id_val = row.get("contrat_id", "")
    contrat_id = "" if pd.isna(contrat_id_val) else str(contrat_id_val).strip()
    
    # Récupérer les infos du contrat si disponible
    contrat_info = ""
    if contrat_id and df_contrats is not None:
        contrat_match = df_contrats[df_contrats["id"] == contrat_id]
        if not contrat_match.empty:
            contrat_row = contrat_match.iloc[0]
            contrat_info = f"{contrat_row['etablissement']} — {contrat_row['enveloppe']}"
        else:
            contrat_info = "Contrat inconnu"

    meta_str = contrat_info

    if is_auto_row and row.get("ticker"):
        error_tickers = st.session_state.get("sync_error_tickers", set())
        ticker = row["ticker"]
        if ticker in error_tickers:
            icon = ":red[:material/sync_problem:]"
        else:
            icon = ":green[:material/published_with_changes:]"
        ticker_line = f"{ticker}"
        if meta_str:
            ticker_line += f" · {meta_str}"

        if cols[0].button(
            row["nom"], 
            key=f"detail_{row['id']}", 
            help="Voir les détails de cet actif", 
            type="tertiary",
            icon=":material/article:",
            icon_position="right",
            width="content",
        ):
            set_asset_detail(row["id"])
            st.rerun()

        # Rendre le ticker cliquable pour ouvrir la page de détail
        with cols[0].container(horizontal=True, width="content",vertical_alignment="center"):

            st.markdown(f"{icon} :small[:grey[{ticker_line}]]")

    else:
        if row["categorie"] == "Immobilier":
            if cols[0].button(
                row["nom"],
                key=f"detail_{row['id']}",
                help="Voir le détail de ce bien",
                type="tertiary",
                icon=":material/article:",
                icon_position="right",

            ):
                set_asset_detail(row["id"])
                st.rerun()
        else:
            cols[0].write(row["nom"])
        if meta_str:
            cols[0].caption(meta_str)
        if row["categorie"] == "Immobilier":
            # ── Métriques locatives ───────────────────────────────────────────
            if row.get("usage") == "locatif":
                metrics = calculate_rental_metrics(row)
                
                loc_parts = []
                if row.get("loyer_mensuel", 0) > 0 and metrics["cout_reel"] > 0:
                    loc_parts.append(f"{metrics['rendement_brut']:.1f} % brut")
                if row.get("loyer_mensuel", 0) > 0:
                    cashflow = metrics["cashflow_mensuel"]
                    sign = "+" if cashflow >= 0 else ""
                    color = "green" if cashflow >= 0 else "red"
                    loc_parts.append(f"Cashflow : :{color}[**{sign}{cashflow:.0f} €/m**]")
                if loc_parts:
                    cols[0].caption(" · ".join(loc_parts))

    # ── Quantité (actifs auto uniquement) ─────────────────────────────────────
    if is_auto_row:
        cols[1].caption(f'{row["quantite"]:g} unités')
        cols[1].caption(f'PRU : {row["pru"]:,.2f} €')

    # ── Prix actuel de l'actif ────────────────────────────────────────────────
    if is_auto_row:
        prix_par_part = row["montant"] / row["quantite"] if row.get("quantite", 0) > 0 else 0
        cols[2].caption(f'Prix : {prix_par_part:,.2f} €')

    # ── PnL (actifs auto avec PRU) ────────────────────────────────────────────
    with cols[3].container(horizontal=True, width="content", vertical_alignment="center"):
        if st.button(
                "",
                key=f"updd_{row['id']}",
                icon=":material/history:",
                help="Mettre à jour à une date",
                type="tertiary"
            ):
                set_dialog_update(row["id"])
                st.rerun()
        st.markdown(f"**{row['montant']:,.2f} €**")

    if is_auto_row and row.get("quantite", 0) > 0 and row.get("pru", 0) > 0:
        pnl_metrics = calculate_auto_asset_pnl(row["montant"], row["pru"], row["quantite"])
        pnl = pnl_metrics["pnl_absolu"]
        pnl_pct = pnl_metrics["pnl_pct"]
        sign_color = "green" if pnl >= 0 else "red"
        sign = "+" if pnl >= 0 else ""
        sign_icon = ":material/trending_up:" if pnl >= 0 else ":material/trending_down:"
        cols[3].markdown(f":{sign_color}-badge[{sign_icon} {sign}{pnl:,.2f} € ({sign}{pnl_pct:.1f}%)]")


    # ── Boutons édition / suppression ─────────────────────────────────────────
    with cols[4].container(horizontal=True, width="content", vertical_alignment="center"):
        if st.button("", key=f"mod_{row['id']}", icon=":material/edit_square:", type="tertiary", help="Modifier l'actif"):
            set_dialog_edit(row["id"])
            st.rerun()

        if st.button("", key=f"del_{row['id']}", icon=":material/delete:", type="tertiary", help="Supprimer l'actif"):
            set_dialog_delete(row["id"])
            st.rerun()


# ── Point d'entrée public ─────────────────────────────────────────────────────

def render(df: pd.DataFrame, invalidate_cache_fn, flash_fn) -> pd.DataFrame:
    from services.assets import compute_total
    from ui.asset_detail import render_asset_detail, is_asset_detail_active, get_current_asset_id

    # Si une page de détail est active, l'afficher
    if is_asset_detail_active():
        asset_id = get_current_asset_id()
        render_asset_detail(asset_id, df)
        return df

    # Charger les contrats une seule fois pour éviter les requêtes multiples
    df_contrats = load_contrats()
    df_emprunts = load_emprunts()

    has_auto_assets = (
        not df.empty
        and df["categorie"].isin(CATEGORIES_AUTO).any()
        and df["ticker"].notna().any()
        and (df["ticker"] != "").any()
    )

    if has_auto_assets and "sync_time" not in st.session_state:
        st.session_state["sync_time"] = "—"
        st.session_state["sync_error_tickers"] = set()


    # ── Métriques de l'onglet Actifs ──────────────────────────────────────────
    total = compute_total(df)

    # PnL global sur les actifs cotés uniquement (ceux avec PRU)
    df_auto = df[df["categorie"].isin(CATEGORIES_AUTO)]
    has_pnl = not df_auto.empty and (df_auto["pru"] > 0).any() and (df_auto["quantite"] > 0).any()

    with st.container(vertical_alignment="center"):
        if has_pnl:
            pnl_global = 0.0
            valeur_achat_totale = 0.0
            
            for _, asset in df_auto.iterrows():
                if asset.get("pru", 0) > 0 and asset.get("quantite", 0) > 0:
                    pnl_metrics = calculate_auto_asset_pnl(asset["montant"], asset["pru"], asset["quantite"])
                    pnl_global += pnl_metrics["pnl_absolu"]
                    valeur_achat_totale += pnl_metrics["valeur_achat"]
            
            pnl_pct = (pnl_global / valeur_achat_totale * 100) if valeur_achat_totale else 0
            sign = "+" if pnl_global >= 0 else ""
            st.metric(label="Total actifs", value=f"{total:,.2f} €",delta=f"{sign}{pnl_global:,.2f} € ({sign}{pnl_pct:.1f}%)")
        else:
            st.metric(label="Total actifs", value=f"{total:,.2f} €")



    st.space(size="small")

    # ── Boutons d'action ──────────────────────────────────────────────────────
    with st.container(horizontal=True, vertical_alignment="center"):
        with st.container(horizontal=True, vertical_alignment="center"):
            if has_auto_assets:
                if st.button(
                    "",
                    icon=":material/refresh:",
                    disabled=not has_auto_assets,
                    help="Actualiser les prix",
                    key="btn_refresh_prices",
                    type="tertiary"
                ):
                    with st.spinner("Récupération des prix…"):
                        df, msg, msg_type = refresh_prices(df)
                    flash_fn(msg, msg_type)
                    st.session_state["sync_time"] = datetime.now().strftime("%H:%M")
                    st.session_state["sync_error_tickers"] = set(
                        msg.replace("Tickers introuvables : ", "").split(", ")
                    ) if msg_type == "warning" else set()
                    invalidate_cache_fn()
                    st.rerun()
                if "sync_time" in st.session_state:
                    st.caption(f"Prix synchronisés à {st.session_state['sync_time']}")


    # ── Liste des actifs ──────────────────────────────────────────────────────
    if df.empty:
        st.info("Aucun actif pour l'instant. Ajoute un actif pour commencer.")

    else:
        categories_presentes = [c for c in CATEGORIES_ASSETS if c in df["categorie"].values]

        for categorie in categories_presentes:
            category_color = CATEGORY_COLOR_MAP.get(categorie, "#CCCCCC")
            st.markdown(
                f"<span style='color:{category_color}; font-size:0.85em;'>●</span> "
                f"<span style='color:{category_color}; font-size:0.85em; text-transform:uppercase; letter-spacing:0.08em;'>{categorie}</span>",
                unsafe_allow_html=True,
            )
            df_cat = df[df["categorie"] == categorie]
            for _, row in df_cat.iterrows():
                with st.container(border=True, vertical_alignment="center"):
                    _render_asset_row(row, df_contrats=df_contrats, df_emprunts=df_emprunts)
            st.space(size="small")

    return df