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
from constants import CATEGORIES_ASSETS, CATEGORIES_AUTO, CATEGORY_COLOR_MAP, PLOTLY_LAYOUT


# ── Ligne d'actif ─────────────────────────────────────────────────────────────

def _render_asset_row(row: pd.Series):
    is_auto_row = row["categorie"] in CATEGORIES_AUTO
    cols = st.columns([4, 2, 2, 2, 1, 1])

    # ── Colonne nom + infos discrètes ─────────────────────────────────────────
    courtier  = str(row.get("courtier",  "") or "").strip()
    enveloppe = str(row.get("enveloppe", "") or "").strip()
    meta_parts = [p for p in [courtier, enveloppe] if p]
    meta_str   = " · ".join(meta_parts)  # ex. "Boursorama · PEA"

    if is_auto_row and row.get("ticker"):
        error_tickers = st.session_state.get("sync_error_tickers", set())
        ticker = row["ticker"]
        sync_dot = " 🔴" if ticker in error_tickers else " 🟢"
        ticker_line = f"{ticker}{sync_dot}"
        if meta_str:
            ticker_line += f" · {meta_str}"
        cols[0].write(row["nom"])
        cols[0].caption(ticker_line)
    else:
        cols[0].write(row["nom"])
        if meta_str:
            cols[0].caption(meta_str)

    # ── Quantité (actifs auto uniquement) ─────────────────────────────────────
    if is_auto_row:
        cols[1].caption(f'{row["quantite"]:g} unités')

    # ── Montant ───────────────────────────────────────────────────────────────
    cols[2].write(f"{row['montant']:,.2f} €")

    # ── PnL (actifs auto avec PRU) ────────────────────────────────────────────
    if is_auto_row and row.get("quantite", 0) > 0 and row.get("pru", 0) > 0:
        valeur_achat = row["pru"] * row["quantite"]
        pnl = row["montant"] - valeur_achat
        pnl_pct = (pnl / valeur_achat * 100) if valeur_achat else 0
        sign_color = "green" if pnl >= 0 else "red"
        sign = "+" if pnl >= 0 else ""
        sign_icon = ":material/trending_up:" if pnl >= 0 else ":material/trending_down:"
        cols[3].markdown(f":{sign_color}-badge[{sign_icon} {sign}{pnl:,.2f} € ({sign}{pnl_pct:.1f}%)]")

    # ── Boutons ───────────────────────────────────────────────────────────────
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


# ── Vue par enveloppe fiscale ─────────────────────────────────────────────────

def _render_enveloppe_metrics(df: pd.DataFrame):
    if df.empty:
        return

    # On ne garde que les lignes avec une enveloppe renseignée
    df_env = df[df["enveloppe"].notna() & (df["enveloppe"].str.strip() != "")]
    if df_env.empty:
        return

    totaux = (
        df_env.groupby("enveloppe")["montant"]
        .sum()
        .sort_values(ascending=False)
    )

    st.subheader("Répartition par enveloppe", anchor=False)

    #afficher un container horizontal avec une metric par enveloppe
    with st.container(horizontal=True):
        for enveloppe, montant in totaux.items():
            st.metric(label=enveloppe, value=f"{montant:,.2f} €", border=True)


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

    total = compute_total(df)
    st.metric(label="Patrimoine total", value=f"{total:,.2f} €")

    if has_auto_assets and "sync_time" in st.session_state:
        st.caption(f"Prix synchronisés à {st.session_state['sync_time']}")

    st.space(size="small")

    if df.empty:
        st.info("Aucun actif enregistré. Utilisez le bouton « Ajouter un actif » pour commencer.")
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
                    _render_asset_row(row)
            st.space(size="small")

    _render_pie_chart(df)
    _render_enveloppe_metrics(df)

    return df