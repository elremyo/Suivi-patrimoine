import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from services.storage import init_storage, download_assets, save_assets
from services.assets import (
    get_assets, add_asset, update_asset, delete_asset,
    compute_total, compute_by_category,
)
from services.historique import (
    init_historique, load_historique, save_snapshot, delete_snapshot,
    get_total_evolution, get_category_evolution, get_snapshot_table,
    get_last_two_snapshots_totals,
)
from services.pricer import refresh_auto_assets, get_name
from constants import CATEGORIES_ASSETS, CATEGORIES_AUTO, CATEGORY_COLORS, PLOTLY_LAYOUT


st.set_page_config(page_title="Suivi Patrimoine", layout="wide")
init_storage()
init_historique()

df = get_assets()
df_hist = load_historique()


def flash(msg: str, type: str = "success"):
    """Stocke un message à afficher après le prochain rerun."""
    st.session_state["_flash"] = {"msg": msg, "type": type}


def show_flash():
    """Affiche et consomme le message flash s'il existe."""
    if "_flash" in st.session_state:
        f = st.session_state.pop("_flash")
        if f["type"] == "success":
            st.toast(f["msg"], icon="✅")
        elif f["type"] == "warning":
            st.toast(f["msg"], icon="⚠️")
        elif f["type"] == "error":
            st.toast(f["msg"], icon="❌")
        elif f["type"] == "info":
            st.toast(f["msg"], icon="ℹ️")


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("Suivi de patrimoine")
    st.divider()

    st.subheader("Ajouter un actif")

    categorie = st.selectbox("Catégorie", options=CATEGORIES_ASSETS, key="add_categorie")
    is_auto = categorie in CATEGORIES_AUTO

    with st.form("add_asset", clear_on_submit=True):
        if is_auto:
            ticker = st.text_input("Ticker *", placeholder="ex. AAPL, BTC-USD, CW8.PA")
            quantite = st.number_input("Quantité", min_value=0.0, step=1.0, format="%g")
            pru = st.number_input("PRU (€)", min_value=0.0, step=1.0, format="%g",
                                  help="Prix de Revient Unitaire.")
            nom = ""
            montant = 0.0
        else:
            nom = st.text_input("Nom *")
            ticker = ""
            quantite = 0.0
            pru = 0.0
            montant = st.number_input("Montant (€)", min_value=0.0, step=100.0)

        if st.form_submit_button("Ajouter", type="primary", use_container_width=True):
            if is_auto and not ticker:
                st.warning("Le ticker est obligatoire.")
            elif not is_auto and not nom:
                st.warning("Le nom est obligatoire.")
            else:
                if is_auto:
                    with st.spinner("Récupération du nom et du prix…"):
                        nom = get_name(ticker)
                        df = add_asset(df, nom, categorie, montant, ticker, quantite, pru)
                        df, errors = refresh_auto_assets(df, CATEGORIES_AUTO)
                        save_assets(df)
                    if errors:
                        flash(f"Actif ajouté ({nom}), mais ticker introuvable : {', '.join(errors)}", type="warning")
                    else:
                        flash(f"Actif ajouté et prix synchronisé ({nom})")
                else:
                    df = add_asset(df, nom, categorie, montant, ticker, quantite, pru)
                    flash("Actif ajouté")
                st.rerun()

    show_flash()

    st.divider()

    st.subheader("Prix")

    has_auto_assets = (
        not df.empty
        and df["categorie"].isin(CATEGORIES_AUTO).any()
        and df["ticker"].notna().any()
        and (df["ticker"] != "").any()
    )

    if st.button("🔄 Actualiser les prix", disabled=not has_auto_assets,
                 use_container_width=True):
        with st.spinner("Récupération des prix…"):
            df, errors = refresh_auto_assets(df, CATEGORIES_AUTO)
            save_assets(df)
        if errors:
            flash(f"Tickers introuvables : {', '.join(errors)}", type="warning")
        else:
            flash("Prix mis à jour")
        st.rerun()

    show_flash()

    st.divider()

    st.subheader("Historique")
    if st.button("📸 Enregistrer un snapshot", disabled=df.empty, use_container_width=True, type="primary"):
        if save_snapshot(df):
            flash("Snapshot enregistré")
            st.rerun()
    st.caption("Un seul snapshot par jour — le dernier écrase le précédent.")

    show_flash()

    st.divider()

    st.subheader("Exporter")
    if st.download_button(
        "Télécharger le patrimoine",
        data=download_assets(df),
        file_name="patrimoine.csv",
        mime="text/csv",
        icon=":material/download:",
        use_container_width=True,
    ):
        pass  # Le téléchargement ne nécessite pas de rerun

# ── Page principale ───────────────────────────────────────────────────────────

st.title("Suivi de patrimoine")

tab_actifs, tab_historique = st.tabs(["📋 Actifs", "📈 Historique"])

# ── Tab Actifs ────────────────────────────────────────────────────────────────

with tab_actifs:

    show_flash()

    st.subheader("Actifs")

    if df.empty:
        st.info("Aucun actif enregistré. Utilisez le panneau latéral pour en ajouter un.")
    else:
        for idx, row in df.iterrows():
            with st.container(border=True, vertical_alignment="center"):
                is_auto_row = row["categorie"] in CATEGORIES_AUTO
                cols = st.columns([4, 2, 2, 2, 1, 1])
                cols[0].write(row["nom"])
                cols[1].write(row["categorie"])
                cols[2].write(f"{row['montant']:,.2f} €")

                if is_auto_row and row.get("quantite", 0) > 0 and row.get("pru", 0) > 0:
                    valeur_achat = row["pru"] * row["quantite"]
                    pnl = row["montant"] - valeur_achat
                    pnl_pct = (pnl / valeur_achat * 100) if valeur_achat else 0
                    color = "#36C28A" if pnl >= 0 else "#E8547A"
                    sign = "+" if pnl >= 0 else ""
                    cols[3].markdown(
                        f"<span style='color:{color}'>{sign}{pnl:,.2f} € ({sign}{pnl_pct:.1f}%)</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    cols[3].write("")

                if cols[4].button("", key=f"mod_{idx}", icon=":material/edit_square:"):
                    st.session_state["editing_idx"] = idx
                if cols[5].button("", key=f"del_{idx}", icon=":material/delete:"):
                    st.session_state["deleting_idx"] = idx

    if "editing_idx" in st.session_state:
        idx = st.session_state["editing_idx"]
        row = df.loc[idx]
        ticker_current = row.get("ticker", "")
        if pd.isna(ticker_current):
            ticker_current = ""
        quantite_current = row.get("quantite", 0.0)
        if pd.isna(quantite_current):
            quantite_current = 0.0
        pru_current = row.get("pru", 0.0)
        if pd.isna(pru_current):
            pru_current = 0.0

        is_auto_edit = row["categorie"] in CATEGORIES_AUTO

        with st.form("edit_asset"):
            if is_auto_edit:
                st.text_input("Nom", value=row["nom"], disabled=True,
                              help="Nom récupéré automatiquement depuis yfinance.")
                ticker = st.text_input("Ticker *", value=ticker_current,
                                       placeholder="ex. AAPL, BTC-USD, CW8.PA")
                quantite = st.number_input("Quantité", min_value=0.0,
                                           value=float(quantite_current), step=1.0, format="%g")
                pru = st.number_input("PRU (€)", min_value=0.0,
                                      value=float(pru_current), step=1.0, format="%g")
                montant = float(row["montant"])
            else:
                nom = st.text_input("Nom *", value=row["nom"])
                ticker = ""
                quantite = 0.0
                pru = 0.0
                montant = st.number_input("Montant (€)", min_value=0.0,
                                          value=float(row["montant"]), step=100.0)
            categorie_edit = st.selectbox("Catégorie", options=CATEGORIES_ASSETS,
                                          index=CATEGORIES_ASSETS.index(row["categorie"]))

            c1, c2 = st.columns(2)
            if c1.form_submit_button("Sauvegarder", type="primary", use_container_width=True):
                if is_auto_edit and not ticker:
                    st.warning("Le ticker est obligatoire.")
                elif not is_auto_edit and not nom:
                    st.warning("Le nom est obligatoire.")
                else:
                    if is_auto_edit:
                        # Si le ticker a changé, on récupère le nouveau nom
                        new_nom = get_name(ticker) if ticker != ticker_current else row["nom"]
                        with st.spinner("Synchronisation du prix…"):
                            df = update_asset(df, idx, new_nom, categorie_edit, montant, ticker, quantite, pru)
                            df, errors = refresh_auto_assets(df, CATEGORIES_AUTO)
                            save_assets(df)
                        if errors:
                            flash(f"Actif modifié, mais ticker introuvable : {', '.join(errors)}", type="warning")
                        else:
                            flash("Actif modifié et prix synchronisé")
                    else:
                        df = update_asset(df, idx, nom, categorie_edit, montant, ticker, quantite, pru)
                        flash("Actif modifié")
                    del st.session_state["editing_idx"]
                    st.rerun()
            if c2.form_submit_button("Annuler", use_container_width=True):
                del st.session_state["editing_idx"]
                st.rerun()

    if "deleting_idx" in st.session_state:
        idx = st.session_state["deleting_idx"]
        row = df.loc[idx]

        with st.container(border=True):
            st.warning(f"Supprimer **{row['nom']}** ? Cette action est irréversible.")
            c1, c2 = st.columns(2)
            if c1.button("Confirmer", key=f"confirm_del_{idx}", type="primary", use_container_width=True):
                df = delete_asset(df, idx)
                flash("Actif supprimé")
                del st.session_state["deleting_idx"]
                st.rerun()
            if c2.button("Annuler", key=f"cancel_del_{idx}", use_container_width=True):
                del st.session_state["deleting_idx"]
                st.rerun()

    st.divider()

    total = compute_total(df)
    dernier, avant_dernier = get_last_two_snapshots_totals(df_hist)

    if dernier and avant_dernier:
        delta_total = dernier["total"] - avant_dernier["total"]
        delta_str = (
            f"{delta_total:+,.2f} € "
            f"({avant_dernier['date'].strftime('%d/%m/%Y')} → {dernier['date'].strftime('%d/%m/%Y')})"
        )
    else:
        delta_str = None

    st.metric(label="Patrimoine total", value=f"{total:,.2f} €", delta=delta_str)

    stats = compute_by_category(df)
    if not stats.empty:
        st.subheader("Répartition par catégorie")

        fig_pie = go.Figure(go.Pie(
            labels=stats["categorie"],
            values=stats["montant"],
            marker=dict(colors=CATEGORY_COLORS[:len(stats)]),
            textinfo="label+percent",
            textfont=dict(color="#E8EAF0", size=13),
            hole=0.35,
        ))
        fig_pie.update_layout(
            **{**PLOTLY_LAYOUT, "margin": dict(l=10, r=10, t=10, b=10)},
            showlegend=False,
        )
        st.plotly_chart(fig_pie, use_container_width=True, config={"staticPlot": True})


# ── Tab Historique ────────────────────────────────────────────────────────────

with tab_historique:

    if df_hist.empty:
        st.info("Aucun historique. Enregistrez un premier snapshot depuis le panneau latéral.")
    else:
        st.subheader("Évolution du patrimoine total")
        total_evo = get_total_evolution(df_hist)
        fig_total = go.Figure()
        fig_total.add_trace(go.Scatter(
            x=total_evo["date"], y=total_evo["total"],
            mode="lines+markers", name="Total",
            line=dict(color=CATEGORY_COLORS[0], width=2),
            marker=dict(size=5),
        ))
        fig_total.update_layout(**PLOTLY_LAYOUT, yaxis_title="Patrimoine (€)", xaxis_title="Date")
        st.plotly_chart(fig_total, use_container_width=True, config={"staticPlot": True})

        st.subheader("Évolution par catégorie")
        cat_evo = get_category_evolution(df_hist)
        fig_cat = go.Figure()
        for i, col in enumerate(cat_evo.columns):
            color = CATEGORY_COLORS[i % len(CATEGORY_COLORS)]
            fig_cat.add_trace(go.Scatter(
                x=cat_evo.index, y=cat_evo[col],
                mode="lines+markers", name=col,
                line=dict(color=color, width=2),
                marker=dict(size=5, color=color),
            ))
        fig_cat.update_layout(
            **PLOTLY_LAYOUT,
            yaxis_title="Montant (€)", xaxis_title="Date",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                        bgcolor="rgba(0,0,0,0)", font=dict(color="#E8EAF0")),
        )
        st.plotly_chart(fig_cat, use_container_width=True, config={"staticPlot": True})

        st.subheader("Tableau des snapshots")
        snap_table = get_snapshot_table(df_hist)
        formatted = snap_table.copy()
        for col in formatted.columns:
            formatted[col] = formatted[col].apply(lambda x: f"{x:,.2f} €")
        st.dataframe(formatted, use_container_width=True)

        with st.expander("Supprimer un snapshot"):
            show_flash()
            dates_dispo = sorted(df_hist["date"].dt.date.unique(), reverse=True)
            date_to_delete = st.selectbox(
                "Choisir la date à supprimer",
                options=dates_dispo,
                format_func=lambda d: d.strftime("%d/%m/%Y"),
            )
            if st.button("Supprimer ce snapshot", icon=":material/delete:"):
                df_hist = delete_snapshot(df_hist, date_to_delete)
                flash("Snapshot supprimé")
                st.rerun()