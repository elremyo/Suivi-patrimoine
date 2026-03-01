"""
ui/tab_actifs.py
───────────────────
Contenu du tab "📋 Actifs" : liste des actifs groupés par catégorie, total patrimoine, camembert.
Les modales sont gérées via ui/asset_form.py.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from services.asset_manager import refresh_prices
from ui.asset_form import set_dialog_edit, set_dialog_delete
from constants import CATEGORIES_ASSETS, CATEGORIES_AUTO, CATEGORY_COLOR_MAP, PLOTLY_LAYOUT


# ── Ligne d'actif (dans le détail d'une catégorie) ───────────────────────────

def _render_asset_row(row: pd.Series):
    is_auto_row = row["categorie"] in CATEGORIES_AUTO
    cols = st.columns([4, 2, 2, 0.5, 0.5])

    if is_auto_row and row.get("ticker"):
        error_tickers = st.session_state.get("sync_error_tickers", set())
        ticker = row["ticker"]
        sync_dot = " 🔴" if ticker in error_tickers else " 🟢"
        cols[0].write(row["nom"])
        cols[0].caption(f'{ticker} · {row["quantite"]:g} unités{sync_dot}')
    else:
        cols[0].write(row["nom"])

    cols[1].write(f"{row['montant']:,.2f} €")

    if is_auto_row and row.get("quantite", 0) > 0 and row.get("pru", 0) > 0:
        valeur_achat = row["pru"] * row["quantite"]
        pnl = row["montant"] - valeur_achat
        pnl_pct = (pnl / valeur_achat * 100) if valeur_achat else 0
        sign_color = "green" if pnl >= 0 else "red"
        sign = "+" if pnl >= 0 else ""
        sign_icon = ":material/trending_up:" if pnl >= 0 else ":material/trending_down:"
        cols[2].markdown(f":{sign_color}-badge[{sign_icon} {sign}{pnl:,.2f} € ({sign}{pnl_pct:.1f}%)]")
    else:
        cols[2].write("")

    if cols[3].button("", key=f"mod_{row['id']}", icon=":material/edit_square:",type="tertiary"):
        set_dialog_edit(row["id"])
        st.rerun()

    if cols[4].button("", key=f"del_{row['id']}", icon=":material/delete:",type="tertiary"):
        set_dialog_delete(row["id"])
        st.rerun()


# ── Bloc catégorie (expander) ─────────────────────────────────────────────────

def _render_category_block(categorie: str, df_cat: pd.DataFrame, total_patrimoine: float):
    """Affiche un expander pour une catégorie avec ses stats et ses actifs."""

    # ── Calculs ───────────────────────────────────────────────────────────────
    montant_cat = df_cat["montant"].sum()
    nb_actifs   = len(df_cat)
    pct         = (montant_cat / total_patrimoine * 100) if total_patrimoine else 0

    # P&L uniquement pour les catégories auto
    pnl_str = ""
    if categorie in CATEGORIES_AUTO:
        mask_pnl = (df_cat["quantite"] > 0) & (df_cat["pru"] > 0)
        if mask_pnl.any():
            valeur_achat = (df_cat.loc[mask_pnl, "pru"] * df_cat.loc[mask_pnl, "quantite"]).sum()
            pnl_total    = df_cat.loc[mask_pnl, "montant"].sum() - valeur_achat
            pnl_pct      = (pnl_total / valeur_achat * 100) if valeur_achat else 0
            sign         = "+" if pnl_total >= 0 else ""
            pnl_color    = "green" if pnl_total >= 0 else "red"
            pnl_icon     = ":material/trending_up:" if pnl_total >= 0 else ":material/trending_down:"
            pnl_str      = f":{pnl_color}-badge[{pnl_icon} {sign}{pnl_total:,.0f} € ({sign}{pnl_pct:.1f}%)]"

    # ── Toggle état ouvert/fermé ──────────────────────────────────────────────
    state_key = f"cat_expanded_{categorie}"
    if state_key not in st.session_state:
        st.session_state[state_key] = False
    is_open = st.session_state[state_key]

    # ── Header cliquable ──────────────────────────────────────────────────────
    color = CATEGORY_COLOR_MAP.get(categorie, "#CCCCCC")
    actifs_label = "actif" if nb_actifs == 1 else "actifs"

    with st.container(border=True):
        cols = st.columns([4, 2, 2, 0.5, 0.5])
        puce_coloree = f"<span style='color:{color}; font-size:1.2em;'>●</span>"
        badge_actifs = f":gray-badge[{nb_actifs} {actifs_label}]"

        cols[0].markdown(f"{puce_coloree} **{categorie}** {badge_actifs}", unsafe_allow_html=True)
        cols[1].markdown(f"**{montant_cat:,.0f} €**")
        #cols[2].markdown(f":gray[{pct:.1f} %]")
        cols[2].markdown(pnl_str if pnl_str else "")

        chevron = ":material/keyboard_arrow_up:" if is_open else ":material/keyboard_arrow_down:"
        cols[3].empty()
        if cols[4].button("", key=f"toggle_{categorie}", icon=chevron,type="secondary"):
            st.session_state[state_key] = not is_open
            st.rerun()

        # ── Détail des actifs ─────────────────────────────────────────────────
        if is_open:
            st.divider()
            for _, row in df_cat.iterrows():
                _render_asset_row(row)
                #afficher un séparateur entre les actifs, sauf après le dernier
                if row.name != df_cat.index[-1]:
                    st.divider()
                else:
                    st.space(size="small")

# ── Graphique camembert ───────────────────────────────────────────────────────

def _render_pie_chart(df: pd.DataFrame):
    from services.assets import compute_by_category
    stats = compute_by_category(df)
    if stats.empty:
        return

    st.subheader("Répartition par catégorie", anchor=False)
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
        st.session_state["prices_refreshed"] = True
        st.session_state["sync_time"] = datetime.now().strftime("%H:%M")
        st.session_state["sync_error_tickers"] = set(
            msg.replace("Tickers introuvables : ", "").split(", ")
        ) if msg_type == "warning" else set()
        if msg_type != "success":
            flash_fn(msg, msg_type)
        invalidate_cache_fn()
        st.rerun()

    if has_auto_assets and "sync_time" not in st.session_state:
        st.session_state["sync_time"] = datetime.now().strftime("%H:%M")
        st.session_state["sync_error_tickers"] = set()

    # ── Total patrimoine ──────────────────────────────────────────────────────
    total = compute_total(df)
    st.metric(label="Patrimoine total", value=f"{total:,.2f} €")

    if has_auto_assets and "sync_time" in st.session_state:
        st.caption(f"Prix synchronisés à {st.session_state['sync_time']}")

    st.space(size="small")

    # ── Liste groupée par catégorie ───────────────────────────────────────────
    if df.empty:
        st.info("Aucun actif enregistré. Utilisez le bouton « Ajouter un actif » pour commencer.")
    else:
        # On respecte l'ordre défini dans CATEGORIES_ASSETS
        categories_presentes = [c for c in CATEGORIES_ASSETS if c in df["categorie"].values]

        for categorie in categories_presentes:
            df_cat = df[df["categorie"] == categorie].reset_index(drop=True)
            _render_category_block(categorie, df_cat, total)

    st.space(size="small")
    _render_pie_chart(df)

    return df