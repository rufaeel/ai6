
import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Load .env locally
load_dotenv()

# Copy Streamlit secrets into env (only if non-empty)
if "OPENAI_API_KEY" in st.secrets and str(st.secrets["OPENAI_API_KEY"]).strip():
    os.environ["OPENAI_API_KEY"] = str(st.secrets["OPENAI_API_KEY"]).strip()
if "POLYGON_API_KEY" in st.secrets and str(st.secrets["POLYGON_API_KEY"]).strip():
    os.environ["POLYGON_API_KEY"] = str(st.secrets["POLYGON_API_KEY"]).strip()

st.set_page_config(page_title="Market AI — Chat + Forecast", layout="wide")
st.title("💬📈 Market AI — Chat + Forecasts")

from tools import get_quote, forecast, news_sentiment, screen_top_movers, default_universe, _download_yf
from llm import respond

tab_chat, tab_analysis = st.tabs(["💬 Chat", "📈 Analysis"])

with st.sidebar:
    st.subheader("API Health Check")
    if st.button("Test OpenAI"):
        try:
            from openai import OpenAI
            key = os.getenv("OPENAI_API_KEY", "").strip()
            client = OpenAI(api_key=key)
            _ = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"system","content":"ping"},{"role":"user","content":"ping"}],
                max_tokens=1,
            )
            st.success("OpenAI ✅")
        except Exception as e:
            st.error(f"OpenAI ❌ {e}")
    if st.button("Test Polygon"):
        try:
            import requests
            key = os.getenv("POLYGON_API_KEY", "").strip()
            r = requests.get(f"https://api.polygon.io/v3/reference/tickers?limit=1&apiKey={key}", timeout=15)
            if r.status_code == 200:
                st.success("Polygon ✅")
            else:
                st.warning(f"Polygon responded with status {r.status_code}")
        except Exception as e:
            st.error(f"Polygon ❌ {e}")

with tab_chat:
    st.caption("Ask things like ‘Forecast CBA.AX 7d’, ‘Top stocks this week’, or ‘News TSLA’.")
    if "history" not in st.session_state:
        st.session_state.history = []
    for role, content in st.session_state.history:
        st.chat_message(role).markdown(content)
    user_text = st.chat_input("Ask a question about stocks, crypto, news, or forecasts…")
    if user_text:
        st.session_state.history.append(("user", user_text))
        st.chat_message("user").write(user_text)
        try:
            answer = respond(user_text, {
                "get_quote": get_quote,
                "forecast": forecast,
                "news_sentiment": news_sentiment,
                "screen_top_movers": screen_top_movers,
                "default_universe": default_universe
            })
        except Exception as e:
            answer = f"Oops, something went wrong: {e}"
        st.session_state.history.append(("assistant", answer))
        st.chat_message("assistant").markdown(answer)

with tab_analysis:
    st.caption("Type a ticker (US: AAPL, TSLA; ASX: CBA.AX, BHP.AX) and choose horizon.")
    col1, col2 = st.columns(2)
    with col1:
        ticker = st.text_input("Ticker", value="AAPL").strip().upper()
    with col2:
        horizon = st.selectbox("Horizon", ["1d", "7d", "30d"], index=1)

    if st.button("Run Analysis"):
        hist = _download_yf(ticker, 365)
        if hist.empty:
            st.error("No historical data found.")
        else:
            st.subheader(f"Historical Chart — {ticker}")
            chart_df = hist[["Date","Close"]].copy().set_index("Date")
            st.line_chart(chart_df)

            st.subheader(f"Forecast — next {horizon}")
            res = forecast(ticker, horizon)
            if not res.get("ok"):
                st.error(res.get("error"))
            else:
                meta = f"Current: {res['current_price']:.2f} | Expected return: {res['expected_return_pct']:.2f}% | Prob(up): {res['prob_up']:.2f}"
                st.write(meta)
                table = pd.DataFrame(res["forecast"])
                st.dataframe(table, use_container_width=True)

                st.subheader("News sentiment (last few headlines)")
                ns = news_sentiment(ticker, limit=5)
                if ns["items"]:
                    for item in ns["items"]:
                        st.write(f"{item['sentiment']:+.2f} — {item['title']}")
                else:
                    st.write("No recent headlines or Polygon key missing.")
