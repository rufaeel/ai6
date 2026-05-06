
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
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
    end = datetime.utcnow()
    start = end - timedelta(days=lookback_days)
    data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True, threads=False)
    if data is None or data.empty:
        return pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data = data.reset_index()
    return data



def _load_prophet():
    try:
        from prophet import Prophet
        return Prophet
    except Exception:
        return None


def _fallback_forecast(df: pd.DataFrame, days: int) -> pd.DataFrame:
    y = df["y"].astype(float).values
    n = len(y)

    if n >= 2:
        x = np.arange(n, dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        future_x = np.arange(n, n + days, dtype=float)
        preds = slope * future_x + intercept
        residuals = y - (slope * x + intercept)
        std = float(np.std(residuals)) if len(residuals) > 1 else max(abs(y[-1]) * 0.01, 1e-6)
    else:
        last = float(y[-1])
        preds = np.full(days, last, dtype=float)
        std = max(abs(last) * 0.01, 1e-6)

    dates = pd.date_range(df["ds"].iloc[-1] + pd.Timedelta(days=1), periods=days, freq="D")
    return pd.DataFrame({
        "ds": dates,
        "yhat": preds,
        "yhat_lower": preds - 1.96 * std,
        "yhat_upper": preds + 1.96 * std,
    })

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
    Prophet = _load_prophet()

    days = _horizon_days(horizon)
    hist = _download_yf(ticker, 500)
    if hist.empty or "Close" not in hist.columns:
        return {"ok": False, "error": f"No historical data for {ticker}"}

    df = hist[["Date", "Close"]].rename(columns={"Date": "ds", "Close": "y"})
    df["ds"] = pd.to_datetime(df["ds"], errors="coerce")
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    df = df.dropna(subset=["ds", "y"]).copy()
    if df.empty:
        return {"ok": False, "error": f"No usable historical data for {ticker}"}
    used_fallback = False
    if Prophet is not None:
        try:
            model = Prophet(daily_seasonality=True, weekly_seasonality=True)
            model.fit(df)
            future = model.make_future_dataframe(periods=days)
            fc = model.predict(future).tail(days)[["ds", "yhat", "yhat_lower", "yhat_upper"]]
        except Exception:
            used_fallback = True
            fc = _fallback_forecast(df, days)
    else:
        used_fallback = True
        fc = _fallback_forecast(df, days)

    current = float(df["y"].iloc[-1])
    mean_pred = float(fc["yhat"].mean())
    expected_return_pct = (mean_pred - current) / current * 100.0

    up_probs = []
    for _, row in fc.iterrows():
        low = float(row["yhat_lower"]); mid = float(row["yhat"]); high = float(row["yhat_upper"])
        p = 0.5
        if mid > current: p += 0.2
        if low > current * 0.995: p += 0.2
        if high > current * 1.01: p += 0.1
        p = max(0.0, min(1.0, p))
        up_probs.append(p)
    prob_up = sum(up_probs)/len(up_probs)

    fc = fc.rename(columns={"ds": "date", "yhat": "pred", "yhat_lower": "lower", "yhat_upper": "upper"})
    fc["date"] = fc["date"].dt.strftime("%Y-%m-%d")

    return {
        "ok": True,
        "ticker": ticker,
        "horizon_days": days,
        "current_price": round(current, 4),
        "expected_return_pct": round(expected_return_pct, 3),
        "prob_up": round(prob_up, 2),
        "used_fallback": used_fallback,
        "forecast": fc.to_dict(orient="records"),
    }

def news_sentiment(ticker_or_query: str, limit: int = 10) -> dict:
    results = []
    if POLYGON_API_KEY:
        url = f"https://api.polygon.io/v2/reference/news?ticker={ticker_or_query.upper()}&limit={limit}&apiKey={POLYGON_API_KEY}"
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                payload = r.json().get("results", [])
                for item in payload:
                    title = item.get("title", "")
                    score = analyzer.polarity_scores(title)["compound"]
                    results.append({"title": title, "url": item.get("article_url"), "sentiment": round(score, 3)})
        except Exception:
            pass
    avg = round(sum(x["sentiment"] for x in results)/len(results), 3) if results else None
    return {"ok": True, "query": ticker_or_query, "avg_sentiment": avg, "items": results}

def screen_top_movers(tickers, horizon: str = "7d"):
    rows = []
    for t in tickers:
        fc = forecast(t, horizon)
        if fc.get("ok"):
            rows.append({
                "Ticker": t,
                "Current": fc["current_price"],
                "Expected %": fc["expected_return_pct"],
                "Prob Up": fc["prob_up"]
            })
    rows = sorted(rows, key=lambda x: x["Expected %"], reverse=True)
    return rows

def default_universe(market: str = "mixed"):
    us = ["AAPL", "MSFT", "TSLA", "NVDA", "AMZN", "META", "GOOGL"]
    asx = ["CBA.AX", "BHP.AX", "WES.AX", "WBC.AX", "CSL.AX", "NAB.AX", "WOW.AX"]
    if market.lower().startswith("us"):
        return us
    if market.lower().startswith("asx"):
        return asx
    return us + asx
