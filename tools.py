import os
import math
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")

# --- Helper ---
def _horizon_days(horizon: str) -> int:
    horizon = (horizon or "").lower().strip()
    if horizon in ["today","1d","1 day"]:
        return 1
    if "week" in horizon or horizon in ["7d","7 days"]:
        return 7
    if "month" in horizon or horizon in ["30d","30 days"]:
        return 30
    # default
    return 7

def _download_yf(ticker: str, lookback_days=365):
    end = datetime.utcnow()
    start = end - timedelta(days=lookback_days)
    data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data = data.reset_index()
    return data

# --- Public tools ---
def get_quote(ticker: str) -> dict:
    """Return last price & daily change using yfinance."""
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
    """Prophet forecast with CI and probability-of-up (simple heuristic)."""
    try:
        from prophet import Prophet
    except Exception as e:
        return {"ok": False, "error": f"Prophet not installed: {e}"}

    days = _horizon_days(horizon)
    hist = _download_yf(ticker, 500)
    if hist.empty or "Close" not in hist.columns:
        return {"ok": False, "error": f"No historical data for {ticker}"}

    df = hist[["Date","Close"]].rename(columns={"Date":"ds","Close":"y"})
    model = Prophet(daily_seasonality=True, weekly_seasonality=True)
    model.fit(df)
    future = model.make_future_dataframe(periods=days)
    fc = model.predict(future).tail(days)[["ds","yhat","yhat_lower","yhat_upper"]]

    current = float(df["y"].iloc[-1])
    mean_pred = float(fc["yhat"].mean())
    expected_return_pct = (mean_pred - current) / current * 100.0

    # very rough probability proxy using CI overlap
    up_probs = []
    for _, row in fc.iterrows():
        low = float(row["yhat_lower"]); mid = float(row["yhat"])
        up_probs.append(1.0 if mid > current and low > current*0.995 else 0.5 if mid > current else 0.3)
    prob_up = sum(up_probs)/len(up_probs)

    fc = fc.rename(columns={"ds":"date","yhat":"pred","yhat_lower":"lower","yhat_upper":"upper"})
    fc["date"] = fc["date"].dt.strftime("%Y-%m-%d")

    return {
        "ok": True,
        "ticker": ticker,
        "horizon_days": days,
        "current_price": round(current, 4),
        "expected_return_pct": round(expected_return_pct, 3),
        "prob_up": round(prob_up, 2),
        "forecast": fc.to_dict(orient="records"),
    }

def news_sentiment(ticker_or_query: str, limit: int = 10) -> dict:
    """Fetch headlines from Polygon (US focus) and score sentiment; fallback to query without ticker param."""
    headers = {}
    results = []
    if POLYGON_API_KEY:
        url = f"https://api.polygon.io/v2/reference/news?ticker={ticker_or_query.upper()}&limit={limit}&apiKey={POLYGON_API_KEY}"
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            payload = r.json().get("results", [])
            for item in payload:
                title = item.get("title","")
                score = analyzer.polarity_scores(title)["compound"]
                results.append({"title": title, "url": item.get("article_url"), "sentiment": round(score, 3)})
    # Average score
    avg = round(sum(x["sentiment"] for x in results)/len(results), 3) if results else None
    return {"ok": True, "query": ticker_or_query, "avg_sentiment": avg, "items": results}

def screen_top_movers(tickers, horizon: str = "7d") -> pd.DataFrame:
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
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values("Expected %", ascending=False)
    return df

def default_universe(market: str = "mixed"):
    us = ["AAPL","MSFT","TSLA","NVDA","AMZN","META","GOOGL"]
    asx = ["CBA.AX","BHP.AX","WES.AX","WBC.AX","CSL.AX","NAB.AX","WOW.AX"]
    if market.lower().startswith("us"):
        return us
    if market.lower().startswith("asx"):
        return asx
    return us + asx
