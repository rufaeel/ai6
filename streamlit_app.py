import streamlit as st
import yfinance as yf
import pandas as pd
from prophet import Prophet
from datetime import datetime, timedelta
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

POLYGON_API_KEY = "Plw9XJ42RE7ktOz7TIxKVTYWxnNi9sZU"
analyzer = SentimentIntensityAnalyzer()

st.set_page_config(page_title="📈 AI Stock/Crypto Forecast & News", layout="wide")
st.title("📈 Smart AI: Forecast + News Sentiment")

prompt = st.chat_input("Ask: 'Forecast TSLA', 'News CBA.AX', 'Top stocks this week'")

if prompt:
    st.chat_message("user").write(prompt)
    forecast_mode = "forecast" in prompt.lower()
    news_mode = "news" in prompt.lower()
    top_mode = "top" in prompt.lower()

    def get_forecast(ticker):
        end = datetime.today()
        start = end - timedelta(days=365)
        data = yf.download(ticker, start=start, end=end)
        if not data.empty:
            df = data.reset_index()[["Date", "Close"]]
            df.columns = ["ds", "y"]
            model = Prophet()
            model.fit(df)
            future = model.make_future_dataframe(periods=7)
            forecast = model.predict(future)
            table = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(7)
            table.columns = ["Date", "Predicted", "Lower Bound", "Upper Bound"]
            return table, df["y"].iloc[-1], forecast["yhat"].iloc[-7:].mean()
        return None, None, None

    if forecast_mode:
        ticker = prompt.upper().split()[-1]
        table, _, _ = get_forecast(ticker)
        if table is not None:
            st.chat_message("assistant").write(f"📈 Prediction for {ticker} (Next 7 Days)")
            st.dataframe(table)
        else:
            st.error("No data found.")

    elif news_mode:
        company = prompt.split("news")[-1].strip()
        st.chat_message("assistant").write(f"📰 News sentiment for '{company}'")
        url = f"https://api.polygon.io/v2/reference/news?ticker={company.upper()}&limit=5&apiKey={POLYGON_API_KEY}"
        res = requests.get(url)
        if res.status_code == 200:
            news = res.json().get("results", [])
            scores = []
            for n in news:
                title = n.get("title", "")
                score = analyzer.polarity_scores(title)["compound"]
                scores.append(score)
                st.write(f"🗞 {title}")
                st.progress((score + 1) / 2)
            if scores:
                st.success(f"📊 Avg Sentiment: {sum(scores)/len(scores):.2f}")
        else:
            st.error("Could not load news.")

    elif top_mode:
        st.chat_message("assistant").write("📊 Scanning top US & ASX stocks for 7-day growth...")
        watchlist = ["AAPL", "MSFT", "TSLA", "NVDA", "CBA.AX", "BHP.AX", "WBC.AX"]
        data = []
        for ticker in watchlist:
            table, current, future_avg = get_forecast(ticker)
            if current and future_avg:
                pct = ((future_avg - current) / current) * 100
                data.append({
                    "Ticker": ticker,
                    "Current Price": round(current, 2),
                    "Forecast (7d Avg)": round(future_avg, 2),
                    "Expected % Change": round(pct, 2)
                })
        df = pd.DataFrame(data).sort_values("Expected % Change", ascending=False)
        st.dataframe(df)
