import os, streamlit as st
from dotenv import load_dotenv

load_dotenv()  # reads .env if present

st.set_page_config(page_title="Market AI – Chat & Forecasts", layout="wide")
st.title("💬 Market AI — ChatGPT‑style forecasts with live data")

# Lazy imports to speed cold start
from tools import get_quote, forecast, news_sentiment, screen_top_movers, default_universe
from llm import respond

st.caption("Tip: Ask things like ‘Forecast CBA.AX 7d’, ‘Top stocks this week’, or ‘News TSLA’.")

# Sidebar config
with st.sidebar:
    st.subheader("Settings")
    st.write("Provide API keys via `.env` or Streamlit secrets.")
    ok = True
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Missing OPENAI_API_KEY")
        ok = False
    if not os.getenv("POLYGON_API_KEY"):
        st.warning("POLYGON_API_KEY not set – news coverage may be limited.")

# Chat state
if "history" not in st.session_state:
    st.session_state.history = []

# Render chat
for role, content in st.session_state.history:
    st.chat_message(role).write(content)

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
import os, streamlit as st

if not os.getenv("OPENAI_API_KEY"):
    try:
        import streamlit as st
        if "OPENAI_API_KEY" not in st.secrets:
            st.error("Missing OPENAI_API_KEY. Add it in Streamlit → Settings → Secrets.")
    except Exception:
        st.error("Missing OPENAI_API_KEY. Set it in your environment or .env file.")
