
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from llm import respond
from tools import default_universe, forecast, get_quote, news_sentiment, screen_top_movers, _download_yf


def _sanitize(value: str | None) -> str:
    return (value or "").strip().replace("\r", "").replace("\n", "")


def _mask(key: str) -> str:
    if not key:
        return "(none)"
        if len(key) <= 10:
        return "****"
     return f"{key[:6]}…{key[-4:]}"


def _set_env_if_present(name: str, value: str | None) -> str:
    cleaned = _sanitize(value)
    if cleaned:
        os.environ[name] = cleaned
    return cleaned


load_dotenv()

st_openai = _sanitize(st.secrets.get("OPENAI_API_KEY", ""))
st_polygon = _sanitize(st.secrets.get("POLYGON_API_KEY", ""))

OPENAI_KEY = _set_env_if_present("OPENAI_API_KEY", st_openai or os.getenv("OPENAI_API_KEY"))
POLYGON_KEY = _set_env_if_present("POLYGON_API_KEY", st_polygon or os.getenv("POLYGON_API_KEY"))

st.set_page_config(page_title="Market AI — Chat + Forecast", layout="wide")
st.title("💬📈 Market AI — Chat + Forecasts")

if OPENAI_KEY.startswith("sk-proj-"):
    st.error(
       "⚠️ Detected an OpenAI project key (`sk-proj-…`). Use a personal `sk-...` key in Streamlit secrets."
    st.stop()

if "history" not in st.session_state:
    st.session_state.history = []


tab_chat, tab_analysis = st.tabs(["💬 Chat", "📈 Analysis"])

with st.sidebar:
    st.subheader("API Health Check")
    if st.button("Test OpenAI"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_KEY)
            _ = client.chat.completions.create(
                model="gpt-4o-mini",
                 messages=[{"role": "system", "content": "ping"}, {"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            st.success("OpenAI ✅")
         except Exception as exc:
            st.error(f"OpenAI ❌ {exc}")
             
    if st.button("Test Polygon"):
        try:
            import requests
             response = requests.get(
                f"https://api.polygon.io/v3/reference/tickers?limit=1&apiKey={POLYGON_KEY}", timeout=15
            )
            if response.status_code == 200:
                st.success("Polygon ✅")
            else:
                 st.warning(f"Polygon responded with status {response.status_code}")
        except Exception as exc:
            st.error(f"Polygon ❌ {exc}")

    st.divider()
    st.caption("Key status (masked)")
    st.write(f"OpenAI key: **{_mask(OPENAI_KEY)}**")
        st.write(
        "Type: "
        + (
            "Personal ✅"
            if OPENAI_KEY.startswith("sk-")
            else ("Project ❌" if OPENAI_KEY.startswith("sk-proj-") else "Missing ❌")
        )
    )
    st.write(f"Polygon key: **{_mask(POLYGON_KEY)}**")

with tab_chat:
    st.caption("Ask things like ‘Forecast CBA.AX 7d’, ‘Top stocks this week’, or ‘News TSLA’.")
  
    for role, content in st.session_state.history:
        st.chat_message(role).markdown(content)
        
    user_text = st.chat_input("Ask a question about stocks, crypto, news, or forecasts…")
    if user_text:
        st.session_state.history.append(("user", user_text))
        st.chat_message("user").write(user_text)
        
        try:
           answer = respond(
                user_text,
                {
                    "get_quote": get_quote,
                    "forecast": forecast,
                    "news_sentiment": news_sentiment,
                    "screen_top_movers": screen_top_movers,
                    "default_universe": default_universe,
                },
            )
        except Exception as exc:
            answer = f"Oops, something went wrong: {exc}"

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
            st.line_chart(hist[["Date", "Close"]].copy().set_index("Date"))

            st.subheader(f"Forecast — next {horizon}")
            result = forecast(ticker, horizon)
            if not result.get("ok"):
                st.error(result.get("error"))
            else:
                 st.write(
                    f"Current: {result['current_price']:.2f} | "
                    f"Expected return: {result['expected_return_pct']:.2f}% | "
                    f"Prob(up): {result['prob_up']:.2f}"
                )
                st.dataframe(pd.DataFrame(result["forecast"]), use_container_width=True)

                st.subheader("News sentiment (last few headlines)")
                 sentiment = news_sentiment(ticker, limit=5)
                if sentiment["items"]:
                    for item in sentiment["items"]:
                        st.write(f"{item['sentiment']:+.2f} — {item['title']}")
                else:
                    st.write("No recent headlines or Polygon key missing.")
