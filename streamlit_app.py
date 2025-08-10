import os, streamlit as st
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
from llm import respond

st.caption("Try: ‘Forecast CBA.AX 7d’, ‘Top stocks this week’, or ‘News TSLA’.")

# Sidebar diagnostics
with st.sidebar:
    st.subheader("Diagnostics")
    st.write({
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "POLYGON_API_KEY": bool(os.getenv("POLYGON_API_KEY"))
    })

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
