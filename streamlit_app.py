
import os
import streamlit as st
from dotenv import load_dotenv

# Load local .env (dev)
load_dotenv()

# Copy Streamlit secrets (cloud) into env so imports see them
if "OPENAI_API_KEY" in st.secrets:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
if "POLYGON_API_KEY" in st.secrets:
    os.environ["POLYGON_API_KEY"] = st.secrets["POLYGON_API_KEY"]

st.set_page_config(page_title="Market AI – Chat & Forecasts", layout="wide")
st.title("💬 Market AI — ChatGPT‑style forecasts with live data")

# Import after env loaded
from tools import get_quote, forecast, news_sentiment, screen_top_movers, default_universe
from llm import respond, SMART_HINTS

st.caption("Ask things like ‘Which ASX stocks will rise most this week’, ‘Forecast TSLA 7d’, or ‘News CBA.AX’.")

# Sidebar diagnostics
with st.sidebar:
    st.subheader("Diagnostics")
    st.write({
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "POLYGON_API_KEY": bool(os.getenv("POLYGON_API_KEY"))
    })
    st.markdown("**Quick actions**")
    if st.button("Top US this week"):
        st.session_state.setdefault("history", []).append(("user", "Which US stocks will rise most this week?"))
    if st.button("Top ASX today"):
        st.session_state.setdefault("history", []).append(("user", "Top ASX gainers today"))
    if st.button("Forecast AAPL 7d"):
        st.session_state.setdefault("history", []).append(("user", "Forecast AAPL 7d"))
    if st.button("News TSLA"):
        st.session_state.setdefault("history", []).append(("user", "News TSLA"))

# Chat state
if "history" not in st.session_state:
    st.session_state.history = []

# Render chat
for role, content in st.session_state.history:
    st.chat_message(role).markdown(content)

# Handle quick actions queued in sidebar
if st.session_state.history and st.session_state.history[-1][0] == "user" and st.session_state.history[-1][1] in SMART_HINTS:
    last = st.session_state.history[-1][1]
    try:
        answer = respond(last, {
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

# Normal chat input
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
