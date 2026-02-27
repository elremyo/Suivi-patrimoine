import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from services.storage import init_storage, download_assets
from services.assets import compute_total, compute_by_category
from services.historique import init_historique, load_historique, build_total_evolution, build_category_evolution
from services.positions import init_positions, load_positions
from services.pricer import fetch_historical_prices
from services.asset_manager import (
    create_auto_asset, create_manual_asset,
    edit_auto_asset, edit_manual_asset,
    remove_asset, refresh_prices,
)
from constants import CATEGORIES_ASSETS, CATEGORIES_AUTO, CATEGORY_COLOR_MAP, PLOTLY_LAYOUT, PERIOD_OPTIONS, PERIOD_DEFAULT


st.set_page_config(page_title="Suivi Patrimoine", layout="wide")
init_storage()
init_historique()
init_positions()


# ── Cache des lectures CSV ────────────────────────────────────────────────────
# Ces fonctions ne relisent le disque qu'une seule fois par session Streamlit.
# Appeler invalidate_data_cache() après chaque écriture pour forcer un rechargement.

@st.cache_data(show_spinner=False)
def cached_load_assets() -> pd.DataFrame:
    from services.assets import get_assets
    return get_assets()


@st.cache_data(show_spinner=False)
def cached_load_historique() -> pd.DataFrame:
    return load_historique()


@st.cache_data(show_spinner=False)
def cached_load_positions() -> pd.DataFrame:
    return load_positions()


def invalidate_data_cache():
    """Vide le cache des lectures CSV. À appeler après toute écriture sur le disque."""
    cached_load_assets.clear()
    cached_load_historique.clear()
    cached_load_positions.clear()


df = cached_load_assets()
df_hist = cached_load_historique()
df_positions = cached_load_positions()


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


def find_row_by_id(df: pd.DataFrame, asset_id: str):
    """
    Retourne (idx, row) pour l'actif correspondant à asset_id.
    Lève une ValueError si l'actif n'est pas trouvé.
    Utiliser l'UUID plutôt que l'index pandas évite de cibler le mauvais actif
    après un reset_index ou une suppression.
    """
    matches = df[df["id"] == asset_id]
    if matches.empty:
        raise ValueError(f"Actif introuvable (id={asset_id}). Il a peut-être déjà été supprimé.")
    idx = matches.index[0]
    return idx, matches.iloc[0]


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
            ticker = ticker.strip().upper()
            quantite = st.number_input("Quantité", min_value=0.0, step=1.0, format="%g")
            pru = st.number_input("PRU (€)", min_value=0.0, step=1.0, format="%g",
                                  help="Prix de Revient Unitaire.")
        else:
            nom = st.text_input("Nom *")
            montant = st.number_input("Montant (€)", min_value=0.0, step=100.0)

        if st.form_submit_button("Ajouter", type="primary", use_container_width=True):
            if is_auto and not ticker:
                st.warning("Le ticker est obligatoire.")
            elif not is_auto and not nom:
                st.warning("Le nom est obligatoire.")
            else:
                if is_auto:
                    with st.spinner("Récupération du nom et du prix…"):
                        df, msg, msg_type = create_auto_asset(df, ticker, quantite, pru, categorie)
                else:
                    df, msg, msg_type = create_manual_asset(df, nom, categorie, montant)
                flash(msg, msg_type)
                invalidate_data_cache()
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

    if st.button("🔄 Actualiser les prix", disabled=not has_auto_assets, width="stretch"):
        with st.spinner("Récupération des prix…"):
            df, msg, msg_type = refresh_prices(df)
        flash(msg, msg_type)
        # ✅ Invalide le cache : les prix ont été mis à jour sur le disque
        invalidate_data_cache()
        st.rerun()

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

    # Refresh automatique au premier chargement de la session
    if "prices_refreshed" not in st.session_state and has_auto_assets:
        with st.spinner("Actualisation des prix en cours…"):
            df, msg, msg_type = refresh_prices(df)
        st.session_state["prices_refreshed"] = True
        if msg_type != "success":
            flash(msg, msg_type)
        # ✅ Invalide le cache : les prix viennent d'être rafraîchis
        invalidate_data_cache()
        st.rerun()

    show_flash()

    st.subheader("Actifs")

    if df.empty:
        st.info("Aucun actif enregistré. Utilisez le panneau latéral pour en ajouter un.")
    else:
        for idx, row in df.iterrows():
            with st.container(border=True, vertical_alignment="center"):
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
                    cols[3].markdown(
                        f":{color}-badge[{icon} {sign}{pnl:,.2f} € ({sign}{pnl_pct:.1f}%)]")
                else:
                    cols[3].write("--")

                # ✅ On stocke l'UUID stable, pas l'index pandas qui peut changer (Action 1)
                if cols[4].button("", key=f"mod_{idx}", icon=":material/edit_square:"):
                    st.session_state["editing_id"] = row["id"]
                if cols[5].button("", key=f"del_{idx}", icon=":material/delete:"):
                    st.session_state["deleting_id"] = row["id"]

    if "editing_id" in st.session_state:
        # ✅ On retrouve la ligne par UUID, pas par index (Action 1)
        try:
            idx, row = find_row_by_id(df, st.session_state["editing_id"])
        except ValueError as e:
            st.error(str(e))
            del st.session_state["editing_id"]
            st.rerun()
        else:
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
                    ticker = ticker.strip().upper()
                    quantite = st.number_input("Quantité", min_value=0.0,
                                               value=float(quantite_current), step=1.0, format="%g")
                    pru = st.number_input("PRU (€)", min_value=0.0,
                                          value=float(pru_current), step=1.0, format="%g")
                    nom = row["nom"]
                else:
                    nom = st.text_input("Nom *", value=row["nom"])
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
                        flash(msg, msg_type)
                        del st.session_state["editing_id"]
                        # ✅ Invalide le cache : l'actif vient d'être modifié
                        invalidate_data_cache()
                        st.rerun()
                if c2.form_submit_button("Annuler", width="stretch"):
                    del st.session_state["editing_id"]
                    st.rerun()

    if "deleting_id" in st.session_state:
        # ✅ On retrouve la ligne par UUID, pas par index (Action 1)
        try:
            idx, row = find_row_by_id(df, st.session_state["deleting_id"])
        except ValueError as e:
            st.error(str(e))
            del st.session_state["deleting_id"]
            st.rerun()
        else:
            with st.container(border=True):
                st.warning(f"Supprimer **{row['nom']}** ? Cette action est irréversible.")
                c1, c2 = st.columns(2)
                if c1.button("Confirmer", key=f"confirm_del_{idx}", type="primary", use_container_width=True):
                    df, msg, msg_type = remove_asset(df, idx, row["id"])
                    flash(msg, msg_type)
                    del st.session_state["deleting_id"]
                    # ✅ Invalide le cache : un actif vient d'être supprimé
                    invalidate_data_cache()
                    st.rerun()
                if c2.button("Annuler", key=f"cancel_del_{idx}", width="stretch"):
                    del st.session_state["deleting_id"]
                    st.rerun()

    st.space(size="small")

    total = compute_total(df)
    st.metric(label="Patrimoine total", value=f"{total:,.2f} €")

    st.space(size="small")

    stats = compute_by_category(df)
    if not stats.empty:
        st.subheader("Répartition par catégorie")
        fig_pie = go.Figure(go.Pie(
            labels=stats["categorie"],
            values=stats["montant"],
            marker=dict(colors=[CATEGORY_COLOR_MAP.get(cat, "#CCCCCC") for cat in stats["categorie"]]),
            textinfo="label+percent",
            textfont=dict(color="#E8EAF0", size=13),
            hole=0.35,
        ))
        fig_pie.update_layout(
            **{**PLOTLY_LAYOUT, "margin": dict(l=10, r=10, t=10, b=10)},
            showlegend=False,
        )
        st.plotly_chart(fig_pie, width="stretch", config={"staticPlot": True})


# ── Tab Historique ────────────────────────────────────────────────────────────

with tab_historique:

    auto_tickers = sorted(
        df[df["categorie"].isin(CATEGORIES_AUTO) & (df["ticker"] != "")]["ticker"]
        .dropna().unique().tolist()
    )

    has_history = not df_hist.empty or (not df_positions.empty and bool(auto_tickers))

    if not has_history:
        st.info("Aucun historique disponible. Ajoutez des actifs et mettez à jour leurs montants pour construire un historique.")
    else:
        # Sélecteur de période
        period_label = st.segmented_control(
            "Période",
            options=list(PERIOD_OPTIONS.keys()),
            default=PERIOD_DEFAULT,
            key="period_selector",
        )
        yf_period, nb_jours = PERIOD_OPTIONS[period_label]

        # Calcul de la date de début pour le filtre
        if nb_jours is not None:
            start_date = pd.Timestamp.today().normalize() - pd.Timedelta(days=nb_jours)
        else:
            start_date = None

        with st.spinner("Reconstruction de l'historique…"):
            df_prices = fetch_historical_prices(tuple(auto_tickers), yf_period) if auto_tickers else pd.DataFrame()
            total_evo = build_total_evolution(df, df_hist, df_positions, df_prices, CATEGORIES_AUTO)
            cat_evo = build_category_evolution(df, df_hist, df_positions, df_prices, CATEGORIES_AUTO)

        # Filtrage par période
        if start_date is not None:
            if not total_evo.empty:
                total_evo = total_evo[total_evo["date"] >= start_date]
            if not cat_evo.empty:
                cat_evo = cat_evo[cat_evo.index >= start_date]

        # Construction des options du multiselect
        options_total = ["Total patrimoine"]
        options_cat = list(cat_evo.columns) if not cat_evo.empty else []
        all_options = options_total + options_cat

        selected = st.multiselect(
            "Séries à afficher",
            options=all_options,
            default=all_options,
            placeholder="Choisir au moins une série…",
        )

        if not selected:
            st.info("Sélectionne au moins une série à afficher.")
        else:
            fig = go.Figure()
            fallback_idx = 0

            for serie in selected:
                if serie == "Total patrimoine" and not total_evo.empty:
                    # Couleur neutre fixe pour le total
                    color = "#E8EAF0"
                    fig.add_trace(go.Scatter(
                        x=total_evo["date"], y=total_evo["total"],
                        mode="lines+markers", name=serie,
                        line=dict(color=color, width=2),
                        marker=dict(size=5),
                    ))
                elif serie in options_cat and not cat_evo.empty and serie in cat_evo.columns:
                    # Couleur fixe par catégorie, fallback sur la palette si inconnue
                    color = CATEGORY_COLOR_MAP.get(serie)
                    if serie not in CATEGORY_COLOR_MAP:
                        fallback_idx += 1
                    fig.add_trace(go.Scatter(
                        x=cat_evo.index, y=cat_evo[serie],
                        mode="lines+markers", name=serie,
                        line=dict(color=color, width=2),
                        marker=dict(size=5),
                    ))

            fig.update_layout(
                **PLOTLY_LAYOUT,
                yaxis_title="Montant (€)", xaxis_title="Date",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                            bgcolor="rgba(0,0,0,0)", font=dict(color="#E8EAF0")),
            )
            st.plotly_chart(fig, width="stretch", config={"staticPlot": True})