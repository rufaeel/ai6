
import os
from datetime import datetime, timedelta
from functools import lru_cache

import pandas as pd
import yfinance as yf
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def _get_secret(name: str) -> str:
    try:
        import streamlit as st
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name, "")

POLYGON_API_KEY = _get_secret("POLYGON_API_KEY")

def _horizon_days(horizon: str) -> int:
    h = (horizon or "").lower().strip()
    if h in ["today", "1d", "1 day"]:
        return 1
    if "week" in h or h in ["7d", "7 days"]:
        return 7
    if "month" in h or h in ["30d", "30 days"]:
        return 30
    return 7

def _download_yf(ticker: str, lookback_days=365):
@lru_cache(maxsize=128)
def _download_yf_cached(ticker: str, lookback_days=365):
    end = datetime.utcnow()
    start = end - timedelta(days=lookback_days)
    data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True, threads=False)
    if data is None or data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data = data.reset_index()
    return data

def _download_yf(ticker: str, lookback_days=365):
    # Return a copy so callers cannot mutate cached frames.
    return _download_yf_cached(ticker, lookback_days).copy()

def get_quote(ticker: str) -> dict:
    df = _download_yf(ticker, 30)
    if df.empty:
        return {"ok": False, "error": f"No data for {ticker}"}
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    price = float(last["Close"])
    change = price - float(prev["Close"])
    pct = (change / float(prev["Close"])) * 100 if prev["Close"] else 0.0
    return {"ok": True, "ticker": ticker, "price": round(price, 4), "day_change_pct": round(pct, 3)}

def forecast(ticker: str, horizon: str = "7d") -> dict:
    try:
        from prophet import Prophet
    except Exception as e:
        return {"ok": False, "error": f"Prophet not installed: {e}"}

    days = _horizon_days(horizon)
    hist = _download_yf(ticker, 500)
    if hist.empty or "Close" not in hist.columns:
        return {"ok": False, "error": f"No historical data for {ticker}"}

    df = hist[["Date", "Close"]].rename(columns={"Date": "ds", "Close": "y"})
    model = Prophet(daily_seasonality=True, weekly_seasonality=True)
    model.fit(df)
