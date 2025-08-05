import streamlit as st
import yfinance as yf
import pandas as pd
from prophet import Prophet
from datetime import datetime, timedelta

st.set_page_config(page_title="📈 Stock & Crypto AI Forecaster", layout="wide")

st.title("💹 Live Stock & Crypto Forecaster")
st.write("Get live forecasts and ask questions about stocks or crypto!")

# Chat interface
prompt = st.chat_input("Ask a question like 'Forecast BTC next week' or 'Show AAPL chart'")

if prompt:
    st.chat_message("user").write(prompt)

# Parse simple prompts
if prompt:
    if "btc" in prompt.lower():
        asset = "BTC-USD"
    elif "aapl" in prompt.lower():
        asset = "AAPL"
    else:
        asset = "BTC-USD"

    st.chat_message("assistant").write(f"Fetching forecast for {asset}...")

    # Load historical data
    end = datetime.today()
    start = end - timedelta(days=365)
    data = yf.download(asset, start=start, end=end)

    if not data.empty:
        df = data.reset_index()[["Date", "Close"]]
        df.columns = ["ds", "y"]

        model = Prophet()
        model.fit(df)
        future = model.make_future_dataframe(periods=7)
        forecast = model.predict(future)

        st.subheader(f"{asset} Forecast (next 7 days)")
        st.line_chart(forecast.set_index("ds")[["yhat"]])
    else:
        st.error(f"No data found for {asset}")
