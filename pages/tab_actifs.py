"""
pages/tab_actifs.py
───────────────────
Contenu du tab "📋 Actifs" : liste des actifs, édition, suppression,
total patrimoine et camembert de répartition.

Point d'entrée unique : render(df, invalidate_cache_fn, flash_fn)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from services.asset_manager import (
    create_auto_asset, create_manual_asset,
    edit_auto_asset, edit_manual_asset,
    remove_asset, refresh_prices,
)
from constants import CATEGORIES_ASSETS, CATEGORIES_AUTO, CATEGORY_COLOR_MAP, PLOTLY_LAYOUT


def _find_row_by_id(df: pd.DataFrame, asset_id: str):
    """
    Retourne (idx, row) pour l'actif correspondant à asset_id.
    Lève une ValueError si l'actif n'est pas trouvé.
    """
    matches = df[df["id"] == asset_id]
    if matches.empty:
        raise ValueError(f"Actif introuvable (id={asset_id}). Il a peut-être déjà été supprimé.")
    return matches.index[0], matches.iloc[0]


def _render_asset_row(df: pd.DataFrame, idx: int, row: pd.Series):
    """Affiche une ligne d'actif avec ses boutons d'action."""
    is_auto_row = row["categorie"] in CATEGORIES_AUTO
    cols = st.columns([4, 2, 2, 2, 1, 1])

    if is_auto_row and row.get("ticker"):
        cols[0].write(row["nom"])
        cols[0].caption(f'{row["ticker"]} · {row["quantite"]:g} unités')
    else:
        cols[0].write(row["nom"])

    cols[1].write(row["categorie"])
    cols[2].write(f"{row['montant']:,.2f} €")

    if is_auto_row and row.get("quantite", 0) > 0 and row.get("pru", 0) > 0:
        valeur_achat = row["pru"] * row["quantite"]
        pnl = row["montant"] - valeur_achat
        pnl_pct = (pnl / valeur_achat * 100) if valeur_achat else 0
        color = "green" if pnl >= 0 else "red"
        sign = "+" if pnl >= 0 else ""
        icon = ":material/trending_up:" if pnl >= 0 else ":material/trending_down:"
        cols[3].markdown(f":{color}-badge[{icon} {sign}{pnl:,.2f} € ({sign}{pnl_pct:.1f}%)]")
    else:
        cols[3].write("--")

    # ✅ UUID stable — pas l'index pandas (Action 1)
    if cols[4].button("", key=f"mod_{idx}", icon=":material/edit_square:"):
        st.session_state["editing_id"] = row["id"]
    if cols[5].button("", key=f"del_{idx}", icon=":material/delete:"):
        st.session_state["deleting_id"] = row["id"]


def _render_edit_form(df: pd.DataFrame, invalidate_cache_fn, flash_fn):
    """Affiche le formulaire d'édition si un actif est en cours de modification."""
    if "editing_id" not in st.session_state:
        return df

    # ✅ Recherche par UUID (Action 1)
    try:
        idx, row = _find_row_by_id(df, st.session_state["editing_id"])
    except ValueError as e:
        st.error(str(e))
        del st.session_state["editing_id"]
        st.rerun()

    ticker_current = row.get("ticker", "") or ""
    if pd.isna(ticker_current):
        ticker_current = ""
    quantite_current = float(row.get("quantite") or 0.0)
    pru_current = float(row.get("pru") or 0.0)
    is_auto_edit = row["categorie"] in CATEGORIES_AUTO

    with st.form("edit_asset"):
        if is_auto_edit:
            st.text_input("Nom", value=row["nom"], disabled=True,
                          help="Nom récupéré automatiquement depuis yfinance.")
            ticker = st.text_input("Ticker *", value=ticker_current,
                                   placeholder="ex. AAPL, BTC-USD, CW8.PA").strip().upper()
            quantite = st.number_input("Quantité", min_value=0.0,
                                       value=quantite_current, step=1.0, format="%g")
            pru = st.number_input("PRU (€)", min_value=0.0,
                                  value=pru_current, step=1.0, format="%g")
            nom = row["nom"]
        else:
            nom = st.text_input("Nom *", value=row["nom"])
            ticker = ""
            quantite = 0.0
            pru = 0.0
            montant = st.number_input("Montant (€)", min_value=0.0,
                                      value=float(row["montant"]), step=100.0)

        categorie_edit = st.selectbox(
            "Catégorie", options=CATEGORIES_ASSETS,
            index=CATEGORIES_ASSETS.index(row["categorie"])
        )

        c1, c2 = st.columns(2)
        if c1.form_submit_button("Sauvegarder", type="primary", use_container_width=True):
            if is_auto_edit and not ticker:
                st.warning("Le ticker est obligatoire.")
            elif not is_auto_edit and not nom:
                st.warning("Le nom est obligatoire.")
            else:
                if is_auto_edit:
                    with st.spinner("Synchronisation du prix…"):
                        df, msg, msg_type = edit_auto_asset(
                            df, idx, row["id"],
                            ticker, ticker_current,
                            quantite, quantite_current,
                            pru, categorie_edit,
                        )
                else:
                    df, msg, msg_type = edit_manual_asset(
                        df, idx, row["id"], nom, categorie_edit, montant
                    )
                flash_fn(msg, msg_type)
                del st.session_state["editing_id"]
                # ✅ Invalide le cache : l'actif vient d'être modifié (Action 2)
                invalidate_cache_fn()
                st.rerun()

        if c2.form_submit_button("Annuler", width="stretch"):
            del st.session_state["editing_id"]
            st.rerun()

    return df


def _render_delete_confirm(df: pd.DataFrame, invalidate_cache_fn, flash_fn):
    """Affiche la confirmation de suppression si un actif est en attente de suppression."""
    if "deleting_id" not in st.session_state:
        return df

    # ✅ Recherche par UUID (Action 1)
    try:
        idx, row = _find_row_by_id(df, st.session_state["deleting_id"])
    except ValueError as e:
        st.error(str(e))
        del st.session_state["deleting_id"]
        st.rerun()

    with st.container(border=True):
        st.warning(f"Supprimer **{row['nom']}** ? Cette action est irréversible.")
        c1, c2 = st.columns(2)
        if c1.button("Confirmer", key=f"confirm_del_{idx}", type="primary", use_container_width=True):
            df, msg, msg_type = remove_asset(df, idx, row["id"])
            flash_fn(msg, msg_type)
            del st.session_state["deleting_id"]
            # ✅ Invalide le cache : un actif vient d'être supprimé (Action 2)
            invalidate_cache_fn()
            st.rerun()
        if c2.button("Annuler", key=f"cancel_del_{idx}", width="stretch"):
            del st.session_state["deleting_id"]
            st.rerun()

    return df


def _render_pie_chart(df: pd.DataFrame):
    """Affiche le camembert de répartition par catégorie."""
    from services.assets import compute_by_category
    stats = compute_by_category(df)
    if stats.empty:
        return

    st.subheader("Répartition par catégorie")
    fig = go.Figure(go.Pie(
        labels=stats["categorie"],
        values=stats["montant"],
        marker=dict(colors=[CATEGORY_COLOR_MAP.get(cat, "#CCCCCC") for cat in stats["categorie"]]),
        textinfo="label+percent",
        textfont=dict(color="#E8EAF0", size=13),
        hole=0.35,
    ))
    fig.update_layout(
        **{**PLOTLY_LAYOUT, "margin": dict(l=10, r=10, t=10, b=10)},
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", config={"staticPlot": True})


# ── Point d'entrée public ─────────────────────────────────────────────────────

def render(df: pd.DataFrame, invalidate_cache_fn, flash_fn) -> pd.DataFrame:
    """
    Affiche le contenu complet du tab Actifs.
    Retourne le DataFrame potentiellement mis à jour après une action.

    Paramètres :
    - df               : DataFrame des actifs courants
    - invalidate_cache_fn : fonction app.py à appeler après une écriture
    - flash_fn         : fonction app.py pour afficher un message toast
    """
    from services.assets import compute_total

    # Refresh automatique des prix au premier chargement de la session
    has_auto_assets = (
        not df.empty
        and df["categorie"].isin(CATEGORIES_AUTO).any()
        and df["ticker"].notna().any()
        and (df["ticker"] != "").any()
    )
    if "prices_refreshed" not in st.session_state and has_auto_assets:
        with st.spinner("Actualisation des prix en cours…"):
            df, msg, msg_type = refresh_prices(df)
        st.session_state["prices_refreshed"] = True
        if msg_type != "success":
            flash_fn(msg, msg_type)
        # ✅ Invalide le cache : les prix viennent d'être rafraîchis (Action 2)
        invalidate_cache_fn()
        st.rerun()

    st.subheader("Actifs")

    if df.empty:
        st.info("Aucun actif enregistré. Utilisez le panneau latéral pour en ajouter un.")
    else:
        for idx, row in df.iterrows():
            with st.container(border=True, vertical_alignment="center"):
                _render_asset_row(df, idx, row)

    df = _render_edit_form(df, invalidate_cache_fn, flash_fn)
    df = _render_delete_confirm(df, invalidate_cache_fn, flash_fn)

    st.space(size="small")

    total = compute_total(df)
    st.metric(label="Patrimoine total", value=f"{total:,.2f} €")

    st.space(size="small")

    _render_pie_chart(df)

    return df