import yfinance as yf
import pandas as pd
import streamlit as st
from constants import CACHE_TTL_SECONDS, PERIOD_OPTIONS, PERIOD_DEFAULT


def get_price(ticker: str) -> float | None:
    """
    Retourne le dernier prix connu pour un ticker yfinance.
    Retourne None si le ticker est invalide ou introuvable.
    """
    try:
        data = yf.Ticker(ticker)
        price = data.fast_info.last_price
        if price and price > 0:
            return round(price, 4)
        return None
    except Exception:
        return None


def get_name(ticker: str) -> str:
    """
    Retourne le nom complet d'un ticker (longName).
    Fallback sur le ticker lui-même si introuvable.
    """
    try:
        info = yf.Ticker(ticker).info
        return info.get("longName") or info.get("shortName") or ticker
    except Exception:
        return ticker


def get_prices_bulk(tickers: list[str]) -> dict[str, float | None]:
    """
    Retourne un dict { ticker: prix } pour une liste de tickers.
    Plus efficace que d'appeler get_price() en boucle.
    """
    if not tickers:
        return {}

    results = {}
    try:
        data = yf.download(tickers, period="1d", progress=False, auto_adjust=True)
        close = data["Close"]
        if isinstance(close, pd.Series):
            close = close.to_frame(name=tickers[0])
        for ticker in tickers:
            if ticker in close.columns and not close[ticker].dropna().empty:
                results[ticker] = round(float(close[ticker].dropna().iloc[-1]), 4)
            else:
                results[ticker] = None
    except Exception:
        for ticker in tickers:
            results[ticker] = None

    return results


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_historical_prices(tickers: tuple, period: str = PERIOD_OPTIONS[PERIOD_DEFAULT][0]) -> pd.DataFrame:
    """
    Récupère les prix de clôture historiques pour une liste de tickers.
    Retourne un DataFrame pivot date × ticker.
    period : "5d", "1mo", "3mo", "6mo", "1y", "max", etc.

    Accepte un tuple (hashable) pour que @st.cache_data puisse construire la clé de cache.
    Le cache est séparé par combinaison (tickers, period).
    """
    if not tickers:
        return pd.DataFrame()
    tickers_list = list(tickers)
    try:
        data = yf.download(tickers_list, period=period, progress=False, auto_adjust=True)
        if data.empty:
            return pd.DataFrame()
        close = data["Close"]
        if isinstance(close, pd.Series):
            close = close.to_frame(name=tickers_list[0])
        close.index = pd.to_datetime(close.index).normalize()
        return close
    except Exception:
        return pd.DataFrame()


def refresh_auto_assets(df: pd.DataFrame, categories_auto: set) -> tuple[pd.DataFrame, list[str]]:
    """
    Met à jour le montant des actifs automatiques (ticker + quantité).
    Retourne le DataFrame mis à jour et la liste des tickers en erreur.
    """
    mask = df["categorie"].isin(categories_auto) & df["ticker"].notna() & (df["ticker"] != "")
    auto_df = df[mask]

    if auto_df.empty:
        return df, []

    tickers = auto_df["ticker"].unique().tolist()
    prices = get_prices_bulk(tickers)

    errors = []
    for idx, row in auto_df.iterrows():
        price = prices.get(row["ticker"])
        if price is not None:
            df.loc[idx, "montant"] = round(price * row["quantite"], 2)
        else:
            errors.append(row["ticker"])

    return df, errors