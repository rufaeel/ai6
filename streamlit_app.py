import streamlit as st
import yfinance as yf
import pandas as pd
from prophet import Prophet
from datetime import datetime, timedelta
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

POLYGON_API_KEY = "Plw9XJ42RE7ktOz7TIxKVTYWxnNi9sZU"

st.set_page_config(page_title="📊 Stock & Crypto AI + News Sentiment", layout="wide")
st.title("📈 Stock & Crypto Forecaster with News Sentiment")

prompt = st.chat_input("Ask: 'Forecast CBA.AX', 'News Tesla', 'Forecast BTC-USD'")

if prompt:
    st.chat_message("user").write(prompt)

    analyzer = SentimentIntensityAnalyzer()
    asset = "AAPL"
    forecast_mode = "forecast" in prompt.lower()
    news_mode = "news" in prompt.lower()

    if forecast_mode:
        # Extract ticker from prompt
        words = prompt.upper().split()
        ticker = next((w for w in words if any(c.isalpha() for c in w)), "AAPL")
        st.chat_message("assistant").write(f"Fetching 7-day forecast for {ticker}...")
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
            st.line_chart(forecast.set_index("ds")[["yhat"]])
        else:
            st.error("No data found.")

    elif news_mode:
        company = prompt.split("news")[-1].strip()
        st.chat_message("assistant").write(f"Pulling news sentiment for '{company}'...")

        url = f"https://api.polygon.io/v2/reference/news?ticker={company.upper()}&limit=5&apiKey={POLYGON_API_KEY}"
        res = requests.get(url)
        if res.status_code == 200:
            news = res.json().get("results", [])
            scores = []
            for n in news:
                headline = n.get("title", "")
                score = analyzer.polarity_scores(headline)["compound"]
                scores.append(score)
                st.write(f"📰 {headline}")
                st.progress((score + 1) / 2)

            if scores:
                avg = sum(scores) / len(scores)
                st.success(f"📊 Average Sentiment: {avg:.2f}")
        else:
            st.error("Could not fetch news from Polygon.")
