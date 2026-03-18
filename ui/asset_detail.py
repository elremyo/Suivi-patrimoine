"""
ui/asset_detail.py
──────────────────
Page de détail pour un actif avec ticker.
Affiche les informations yfinance enrichies : graphique historique des prix, capitalisation.
Accessible uniquement pour les actifs automatiques (Actions & Fonds, Crypto).
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from services.pricer import fetch_historical_prices, get_price, get_name
from constants import PERIOD_OPTIONS, PERIOD_DEFAULT, PLOTLY_LAYOUT, CATEGORIES_AUTO, CACHE_TTL_SECONDS

@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_asset_info(ticker: str) -> dict:
    """
    Récupère les informations détaillées d'un actif depuis yfinance.
    Retourne un dict avec les infos principales ou None si erreur.
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info
        fast = t.fast_info
        
        # Prix actuel
        current_price = fast.last_price if fast.last_price else None
        

        return {
            "ticker": ticker,
            "name": info.get("longName") or info.get("shortName") or ticker,
            "current_price": current_price,
            "currency": fast.currency or info.get("currency", "EUR"),
            "market_cap": info.get("marketCap") or info.get("totalAssets"),
            "volume": info.get("volume"),
            "sector": info.get("sector") or info.get("category"),
            "industry": info.get("industry") or info.get("categoryName"),
            "description": info.get("longBusinessSummary", "") or info.get("objective", ""),
            "website": info.get("website"),
        }
    except Exception as e:
        st.error(f"Erreur lors de la récupération des informations pour {ticker}: {e}")
        return None


def render_price_chart(historical_data: pd.DataFrame, ticker: str, pru: float = None):
    """
    Affiche le graphique historique des prix.
    """
    if historical_data.empty:
        st.warning("Aucune donnée historique disponible")
        return
    
    # Normaliser les dates des données historiques
    historical_data.index = historical_data.index.tz_localize(None)
    
    # Création du graphique
    fig = go.Figure()
    
    # Graphique des prix
    fig.add_trace(
        go.Scatter(
            x=historical_data.index,
            y=historical_data[ticker],
            mode='lines',
            name='Prix',
            line=dict(color='#85357d', width=2)
        )
    )
    
    # Ajouter la ligne horizontale du PRU si disponible
    if pru and pru > 0:
        fig.add_hline(
            y=pru,
            line_dash="dash",
            line_color="orange",
            annotation_text=f"PRU: {pru:.4f} €",
            annotation_position="top right"
        )
    
    # Mise en page
    fig.update_layout(
        title=None,
        height=400,
        **PLOTLY_LAYOUT
    )

    fig.update_yaxes(
        ticksuffix=" €",
        tickformat=",.0f"
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"staticPlot": True})

@st.fragment
def _render_chart_section(ticker: str, pru: float = None):
    # Sélecteur de période format radio (comme dans l'onglet Historique)
    selected_period = st.radio(
        "Période",
        options=list(PERIOD_OPTIONS.keys()),
        index=list(PERIOD_OPTIONS.keys()).index(PERIOD_DEFAULT),
        horizontal=True,
        key="asset_detail_period_selector",
        label_visibility="collapsed"
    )
    period = PERIOD_OPTIONS[selected_period][0]
    
    with st.spinner("Chargement des données historiques..."):
        historical_data = fetch_historical_prices((ticker,), period)
    
    if not historical_data.empty:
        render_price_chart(historical_data, ticker, pru)
    else:
        st.warning("Aucune donnée historique disponible pour cette période")

def render_asset_info(asset_info: dict):
    """
    Affiche les informations principales de l'actif dans des métriques.
    """
    if not asset_info:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Prix actuel
    with col1:
        price = asset_info.get("current_price", 0)
        currency = asset_info.get("currency", "EUR")
        st.metric(
            "Prix actuel",
            f"{price:,.4f} {currency}" if currency != "EUR" else f"{price:,.4f} €"
        )
    
    # Capitalisation boursière
    with col2:
        market_cap = asset_info.get("market_cap")
        if market_cap and market_cap > 0:
            if market_cap >= 1e9:
                cap_str = f"{market_cap/1e9:,.1f} Md€"
            elif market_cap >= 1e6:
                cap_str = f"{market_cap/1e6:,.1f} M€"
            else:
                cap_str = f"{market_cap:,.0f} €"
            st.metric("Capitalisation", cap_str)
        else:
            st.metric("Capitalisation", "N/A")
    
    # Volume
    with col3:
        volume = asset_info.get("volume")
        if volume and volume > 0:
            if volume >= 1e6:
                vol_str = f"{volume/1e6:,.1f} M"
            elif volume >= 1e3:
                vol_str = f"{volume/1e3:,.1f} K"
            else:
                vol_str = f"{volume:,.0f}"
            st.metric("Volume", vol_str)
        else:
            st.metric("Volume", "N/A")
    
    # Secteur
    with col4:
        sector = asset_info.get("sector")
        st.metric("Secteur", sector if sector else "N/A")

def _render_immo_detail(asset: pd.Series):
    """Page de détail pour un bien immobilier."""
    from services.db_emprunts import load_emprunts

    # ── Bouton retour + titre ─────────────────────────────────────────────────
    with st.container(horizontal=True, vertical_alignment="bottom"):
        if st.button("← Retour", key="btn_back_immo", type="secondary"):
            if "_asset_detail" in st.session_state:
                del st.session_state["_asset_detail"]
            st.rerun()
        usage_label = "Résidence principale" if asset.get("usage") == "residence_principale" else "Locatif"
        st.header(f"{asset['nom']}", anchor=False)
    
    st.divider()

    # ── Bloc 1 : Identité ─────────────────────────────────────────────────────
    st.subheader("Identité du bien", anchor=False)
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        type_bien = str(asset.get("type_bien") or "—").capitalize()
        c1.metric("Type", type_bien)
        superficie = asset.get("superficie_m2")
        c2.metric("Superficie", f"{float(superficie):.0f} m²" if superficie and float(superficie) > 0 else "—")
        c3.metric("Usage", usage_label)
        adresse = str(asset.get("adresse") or "—").strip()
        c4.metric("Adresse", adresse if adresse else "—")

    st.space(size="small")

    # ── Bloc 2 : Valorisation ─────────────────────────────────────────────────
    st.subheader("Valorisation", anchor=False)
    with st.container(border=True):
        valeur_actuelle = float(asset.get("montant") or 0)
        prix_achat = float(asset.get("prix_achat") or 0)
        frais_notaire = float(asset.get("frais_notaire") or 0)
        montant_travaux = float(asset.get("montant_travaux") or 0)
        cout_reel = prix_achat + frais_notaire + montant_travaux
        plus_value = valeur_actuelle - cout_reel
        pv_pct = (plus_value / cout_reel * 100) if cout_reel > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Valeur actuelle", f"{valeur_actuelle:,.0f} €")
        c2.metric("Prix d'achat", f"{prix_achat:,.0f} €")
        notaire_str = f"dont {frais_notaire:,.0f} € notaire" if frais_notaire > 0 else ""
        travaux_str = f"+ {montant_travaux:,.0f} € travaux" if montant_travaux > 0 else ""
        detail_cout = " · ".join(filter(None, [notaire_str, travaux_str]))
        c3.metric("Coût réel", f"{cout_reel:,.0f} €", help=detail_cout if detail_cout else None)
        sign = "+" if plus_value >= 0 else ""
        c4.metric("Plus-value latente", f"{sign}{plus_value:,.0f} €", delta=f"{sign}{pv_pct:.1f} %")

    st.space(size="small")

    # ── Bloc 3 : Emprunt lié ──────────────────────────────────────────────────
    emprunt_id = asset.get("emprunt_id")
    if emprunt_id and not pd.isna(emprunt_id):
        df_emprunts = load_emprunts()
        emp = df_emprunts[df_emprunts["id"] == str(emprunt_id)]
        if not emp.empty:
            e = emp.iloc[0]
            st.subheader("Emprunt lié", anchor=False)
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns(4)
                crd = float(e.get("capital_restant_du") or 0)
                mensualite = float(e.get("mensualite") or 0)
                taux = float(e.get("taux_annuel") or 0)
                date_fin = e.get("date_fin")
                date_fin_str = pd.Timestamp(date_fin).strftime("%m/%Y") if date_fin and not pd.isna(date_fin) else "—"
                c1.metric("Capital restant dû", f"{crd:,.0f} €")
                c2.metric("Mensualité", f"{mensualite:,.0f} €/mois")
                c3.metric("Taux annuel", f"{taux:.2f} %")
                c4.metric("Fin prévue", date_fin_str)
            st.space(size="small")

    # ── Bloc 4 : Rendement locatif ────────────────────────────────────────────
    if asset.get("usage") == "locatif":
        loyer = float(asset.get("loyer_mensuel") or 0)
        charges = float(asset.get("charges_mensuelles") or 0)
        taxe = float(asset.get("taxe_fonciere_annuelle") or 0)

        st.subheader("Rendement locatif", anchor=False)
        with st.container(border=True):
            c1, c2, c3 = st.columns(3)
            c1.metric("Loyer mensuel brut", f"{loyer:,.0f} €" if loyer > 0 else "—")
            c2.metric("Charges mensuelles", f"{charges:,.0f} €" if charges > 0 else "—")
            c3.metric("Taxe foncière", f"{taxe:,.0f} €/an" if taxe > 0 else "—")

            if loyer > 0:
                st.divider()
                c1, c2 = st.columns(2)
                if cout_reel > 0:
                    rendement_brut = loyer * 12 / cout_reel * 100
                    c1.metric("Rendement brut", f"{rendement_brut:.2f} %", help="Loyer annuel ÷ coût réel d'acquisition")
                mensualite_emp = 0.0
                if emprunt_id and not pd.isna(emprunt_id):
                    df_emprunts = load_emprunts()
                    emp = df_emprunts[df_emprunts["id"] == str(emprunt_id)]
                    if not emp.empty:
                        mensualite_emp = float(emp.iloc[0]["mensualite"])
                cashflow = loyer - charges - taxe / 12 - mensualite_emp
                sign = "+" if cashflow >= 0 else ""
                c2.metric("Cashflow mensuel", f"{sign}{cashflow:,.0f} €", delta=f"{sign}{cashflow:,.0f} €")



def render_asset_detail(asset_id: str, df: pd.DataFrame):
    """
    Point d'entrée principal pour afficher la page de détail d'un actif.
    """
    # Récupérer l'actif depuis le DataFrame
    asset_row = df[df["id"] == asset_id]
    
    if asset_row.empty:
        st.error(f"Actif avec ID {asset_id} introuvable")
        return
    
    asset = asset_row.iloc[0]
    
    # Dispatcher vers la page immo si nécessaire
    if asset["categorie"] == "Immobilier":
        _render_immo_detail(asset)
        return

    # Vérifier que c'est un actif automatique avec ticker
    if asset["categorie"] not in CATEGORIES_AUTO or not asset.get("ticker"):
        st.error("La page de détail n'est disponible que pour les actifs avec ticker")
        return
    
    ticker = asset["ticker"]
    
    # En-tête avec bouton retour
    with st.container(horizontal=True, vertical_alignment="bottom"):
        if st.button("← Retour", key="btn_back_detail", type="secondary"):
            if "_asset_detail" in st.session_state:
                del st.session_state["_asset_detail"]
            st.rerun()
    
        st.header(f"{asset['nom']}", anchor=False)

    st.divider()
    
    # Récupération des informations
    with st.spinner("Chargement des informations..."):
        asset_info = get_asset_info(ticker)
    
    if not asset_info:
        st.error("Impossible de récupérer les informations de cet actif")
        return
    

    
    # Informations principales
    render_asset_info(asset_info)
    
    # Graphique historique
    st.subheader("Graphique historique", anchor=False)

    _render_chart_section(ticker, asset.get("pru"))

    # Informations complémentaires
    
    if asset_info.get("industry"):
        st.write("**Industrie :**", asset_info["industry"])
    
    if asset_info.get("website"):
        st.write("**Site web :**", f"[{asset_info['website']}]({asset_info['website']})")
    
    if asset_info.get("description"):
        st.write("**Description :**")
        st.caption(asset_info["description"][:500] + "..." if len(asset_info["description"]) > 500 else asset_info["description"])
    
    # Performance dans le portefeuille
    if asset.get("pru") and asset.get("quantite"):
        st.subheader("Performance dans votre portefeuille", anchor=False)
        
        col_perf1, col_perf2, col_perf3 = st.columns(3)
        
        # Valeur d'achat
        valeur_achat = asset["pru"] * asset["quantite"]
        col_perf1.metric("Valeur d'achat", f"{valeur_achat:,.2f} €")
        
        # Valeur actuelle
        valeur_actuelle = asset["montant"]
        col_perf2.metric("Valeur actuelle", f"{valeur_actuelle:,.2f} €")
        
        # PnL
        pnl = valeur_actuelle - valeur_achat
        pnl_pct = (pnl / valeur_achat * 100) if valeur_achat > 0 else 0
        sign = "+" if pnl >= 0 else ""
        col_perf3.metric(
            "Plus/Moins-value",
            f"{sign}{pnl:,.2f} € ({sign}{pnl_pct:.1f}%)",
            delta=f"{sign}{pnl:,.2f} €"
        )


def set_asset_detail(asset_id: str):
    """
    Définit l'actif à afficher en détail via le session state.
    """
    st.session_state["_asset_detail"] = asset_id


def is_asset_detail_active() -> bool:
    """
    Vérifie si une page de détail d'actif est active.
    """
    return "_asset_detail" in st.session_state


def get_current_asset_id() -> str | None:
    """
    Retourne l'ID de l'actif actuellement affiché en détail.
    """
    return st.session_state.get("_asset_detail")
