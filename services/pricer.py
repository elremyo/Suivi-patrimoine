import re
import yfinance as yf
import pandas as pd
import streamlit as st
from constants import CACHE_TTL_SECONDS, PERIOD_OPTIONS, PERIOD_DEFAULT

# Ticker valide : lettres, chiffres, tirets, points, carets — 1 à 20 caractères
# Exemples valides : AAPL, BTC-USD, CW8.PA, ^FCHI
_TICKER_PATTERN = re.compile(r"^[A-Z0-9\.\-\^]{1,20}$")


def validate_ticker(ticker: str) -> tuple[bool, str]:
    """
    Vérifie que le ticker a un format acceptable avant d'appeler yfinance.
    Retourne (True, "") si valide, (False, message_erreur) sinon.
    """
    if not ticker:
        return False, "Le ticker ne peut pas être vide."
    if not _TICKER_PATTERN.match(ticker):
        return False, f"Ticker invalide : « {ticker} ». Utilise uniquement des lettres, chiffres, tirets ou points (ex. AAPL, BTC-USD, CW8.PA)."
    return True, ""


def lookup_ticker(ticker: str) -> dict | None:
    """
    Interroge yfinance pour valider l'existence d'un ticker et récupérer ses infos.
    Retourne un dict {ticker, name, price, currency} ou None si introuvable.
    """
    try:
        t = yf.Ticker(ticker)
        price = t.fast_info.last_price
        if not price or price <= 0:
            return None
        info = t.info
        name = info.get("longName") or info.get("shortName") or ticker
        currency = info.get("currency") or ""
        return {
            "ticker": ticker,
            "name": name,
            "price": round(price, 4),
            "currency": currency,
        }
    except Exception:
        return None


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


def _fetch_exchange_rates(currencies: set[str]) -> dict[str, float]:
    """
    Récupère les taux de change vers EUR pour un ensemble de devises.
    Utilise les tickers Yahoo Finance du type USDEUR=X.
    Retourne un dict { "USD": 0.92, "GBP": 1.17, ... }.
    EUR → EUR = 1.0 (pas d'appel nécessaire).
    """
    non_eur = {c for c in currencies if c and c != "EUR"}
    rates = {"EUR": 1.0}

    if not non_eur:
        return rates

    fx_tickers = [f"{c}EUR=X" for c in non_eur]
    try:
        data = yf.download(fx_tickers, period="1d", progress=False, auto_adjust=True)
        close = data["Close"]
        if isinstance(close, pd.Series):
            # Un seul ticker FX
            fx_ticker = fx_tickers[0]
            currency = fx_ticker.replace("EUR=X", "")
            if not close.dropna().empty:
                rates[currency] = round(float(close.dropna().iloc[-1]), 6)
        else:
            for fx_ticker in fx_tickers:
                currency = fx_ticker.replace("EUR=X", "")
                if fx_ticker in close.columns and not close[fx_ticker].dropna().empty:
                    rates[currency] = round(float(close[fx_ticker].dropna().iloc[-1]), 6)
    except Exception:
        pass

    return rates


def get_prices_bulk(tickers: list[str]) -> dict[str, dict | None]:
    """
    Retourne un dict { ticker: { "price": float, "currency": str } } pour une liste de tickers.
    Retourne None pour les tickers en erreur.
    """
    if not tickers:
        return {}

    results = {}
    try:
        data = yf.download(tickers, period="1d", progress=False, auto_adjust=True)
        close = data["Close"]
        if isinstance(close, pd.Series):
            close = close.to_frame(name=tickers[0])

        # Récupération des devises via fast_info (appel léger)
        currencies = {}
        for ticker in tickers:
            try:
                currencies[ticker] = yf.Ticker(ticker).fast_info.currency or "EUR"
            except Exception:
                currencies[ticker] = "EUR"

        for ticker in tickers:
            if ticker in close.columns and not close[ticker].dropna().empty:
                results[ticker] = {
                    "price": round(float(close[ticker].dropna().iloc[-1]), 4),
                    "currency": currencies.get(ticker, "EUR"),
                }
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
    Les prix sont convertis en EUR si la devise du ticker n'est pas EUR.
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

        # Récupération des devises
        currencies = {}
        for ticker in tickers_list:
            try:
                currencies[ticker] = yf.Ticker(ticker).fast_info.currency or "EUR"
            except Exception:
                currencies[ticker] = "EUR"

        # Récupération des taux de change historiques
        non_eur_currencies = {c for c in currencies.values() if c and c != "EUR"}
        fx_rates_hist: dict[str, pd.Series] = {}

        if non_eur_currencies:
            fx_tickers = [f"{c}EUR=X" for c in non_eur_currencies]
            try:
                fx_data = yf.download(fx_tickers, period=period, progress=False, auto_adjust=True)
                if not fx_data.empty:
                    fx_close = fx_data["Close"]
                    if isinstance(fx_close, pd.Series):
                        fx_ticker = fx_tickers[0]
                        currency = fx_ticker.replace("EUR=X", "")
                        fx_close.index = pd.to_datetime(fx_close.index).normalize()
                        fx_rates_hist[currency] = fx_close
                    else:
                        for fx_ticker in fx_tickers:
                            currency = fx_ticker.replace("EUR=X", "")
                            if fx_ticker in fx_close.columns:
                                s = fx_close[fx_ticker].copy()
                                s.index = pd.to_datetime(s.index).normalize()
                                fx_rates_hist[currency] = s
            except Exception:
                pass

        # Conversion colonne par colonne
        for ticker in tickers_list:
            currency = currencies.get(ticker, "EUR")
            if currency == "EUR" or currency not in fx_rates_hist:
                continue
            fx_series = fx_rates_hist[currency].reindex(close.index, method="ffill")
            close.loc[:, ticker] = (close[ticker] * fx_series).round(4)

        return close
    except Exception:
        return pd.DataFrame()


def refresh_auto_assets(df: pd.DataFrame, categories_auto: set) -> tuple[pd.DataFrame, list[str]]:
    """
    Met à jour le montant des actifs automatiques (ticker + quantité).
    Convertit les prix en EUR si nécessaire.
    Retourne le DataFrame mis à jour et la liste des tickers en erreur.
    """
    mask = df["categorie"].isin(categories_auto) & df["ticker"].notna() & (df["ticker"] != "")
    auto_df = df[mask]

    if auto_df.empty:
        return df, []

    tickers = auto_df["ticker"].unique().tolist()
    prices_data = get_prices_bulk(tickers)

    # Récupération des taux de change pour toutes les devises non-EUR trouvées
    all_currencies = {
        v["currency"] for v in prices_data.values()
        if v is not None and v.get("currency")
    }
    fx_rates = _fetch_exchange_rates(all_currencies)

    errors = []
    for idx, row in auto_df.iterrows():
        data = prices_data.get(row["ticker"])
        if data is not None:
            price = data["price"]
            currency = data["currency"]
            rate = fx_rates.get(currency, 1.0)
            price_eur = round(price * rate, 4)
            df.loc[idx, "montant"] = round(price_eur * row["quantite"], 2)
        else:
            errors.append(row["ticker"])

    return df, errors