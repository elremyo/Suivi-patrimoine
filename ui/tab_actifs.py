"""
ui/tab_actifs.py
───────────────────
Contenu du tab "📋 Actifs" : liste des actifs, total patrimoine, camembert.
Les modales sont gérées via ui/asset_form.py.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from services.asset_manager import refresh_prices
from ui.asset_form import set_dialog_edit, set_dialog_delete
from constants import CATEGORIES_AUTO, CATEGORY_COLOR_MAP, PLOTLY_LAYOUT


# ── Ligne d'actif ─────────────────────────────────────────────────────────────

def _render_asset_row(row: pd.Series):
    is_auto_row = row["categorie"] in CATEGORIES_AUTO
    cols = st.columns([4, 2, 2, 2, 1, 1])

    if is_auto_row and row.get("ticker"):
        # Récupère les tickers en erreur depuis la session
        error_tickers = st.session_state.get("sync_error_tickers", set())
        ticker = row["ticker"]
        sync_dot = " 🔴" if ticker in error_tickers else " 🟢"
        cols[0].write(row["nom"])
        cols[0].caption(f'{ticker} · {row["quantite"]:g} unités{sync_dot}')
    else:
        cols[0].write(row["nom"])

    #write avec une puce colorée selon la catégorie
    category_color = CATEGORY_COLOR_MAP.get(row["categorie"], "#CCCCCC")
    cols[1].markdown(f"<span style='color:{category_color}'>●</span> {row['categorie']}", unsafe_allow_html=True)
    cols[2].write(f"{row['montant']:,.2f} €")

    if is_auto_row and row.get("quantite", 0) > 0 and row.get("pru", 0) > 0:
        valeur_achat = row["pru"] * row["quantite"]
        pnl = row["montant"] - valeur_achat
        pnl_pct = (pnl / valeur_achat * 100) if valeur_achat else 0
        sign_color = "green" if pnl >= 0 else "red"
        sign = "+" if pnl >= 0 else ""
        sign_icon = ":material/trending_up:" if pnl >= 0 else ":material/trending_down:"
        cols[3].markdown(f":{sign_color}-badge[{sign_icon} {sign}{pnl:,.2f} € ({sign}{pnl_pct:.1f}%)]")
    else:
        cols[3].write("--")

    if cols[4].button("", key=f"mod_{row['id']}", icon=":material/edit_square:"):
        set_dialog_edit(row["id"])
        st.rerun()

    if cols[5].button("", key=f"del_{row['id']}", icon=":material/delete:"):
        set_dialog_delete(row["id"])
        st.rerun()


# ── Graphique camembert ───────────────────────────────────────────────────────

def _render_pie_chart(df: pd.DataFrame):
    from services.assets import compute_by_category
    stats = compute_by_category(df)
    if stats.empty:
        return

    st.subheader("Répartition par catégorie",anchor=False)
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
    from services.assets import compute_total

    has_auto_assets = (
        not df.empty
        and df["categorie"].isin(CATEGORIES_AUTO).any()
        and df["ticker"].notna().any()
        and (df["ticker"] != "").any()
    )
    if "prices_refreshed" not in st.session_state and has_auto_assets:
        with st.spinner("Actualisation des prix en cours…"):
            df, msg, msg_type = refresh_prices(df)
        # Stocke l'heure et les erreurs de synchro
        st.session_state["prices_refreshed"] = True
        st.session_state["sync_time"] = datetime.now().strftime("%H:%M")
        st.session_state["sync_error_tickers"] = set(
            msg.replace("Tickers introuvables : ", "").split(", ")
        ) if msg_type == "warning" else set()
        if msg_type != "success":
            flash_fn(msg, msg_type)
        invalidate_cache_fn()
        st.rerun()

    # Stocke aussi l'heure lors d'un refresh manuel (bouton sidebar)
    # → géré via flash, mais on met à jour sync_time ici si absent
    if has_auto_assets and "sync_time" not in st.session_state:
        st.session_state["sync_time"] = datetime.now().strftime("%H:%M")
        st.session_state["sync_error_tickers"] = set()

    total = compute_total(df)
    st.metric(label="Patrimoine total", value=f"{total:,.2f} €")

    # Indicateur de synchro global — discret, sous le total
    if has_auto_assets and "sync_time" in st.session_state:
        st.caption(f"Prix synchronisés à {st.session_state['sync_time']}")

    st.space(size="small")

    if df.empty:
        st.info("Aucun actif enregistré. Utilisez le bouton « Ajouter un actif » pour commencer.")
    else:
        for _, row in df.iterrows():
            with st.container(border=True, vertical_alignment="center"):
                _render_asset_row(row)

    st.space(size="small")
    _render_pie_chart(df)

    return df