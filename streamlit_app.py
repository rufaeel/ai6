# ----- BEGIN INLINE DIAGNOSTICS + FORCE FIX -----
import os, streamlit as st

def _mask(v): 
    v = v or ""
    return (v[:6] + "…" + v[-6:]) if len(v) > 12 else ("(none)" if not v else "****")

secret_key = str(st.secrets.get("OPENAI_API_KEY", "")).strip()
env_key    = (os.getenv("OPENAI_API_KEY") or "").strip()

# Show what the app is actually seeing (masked)
with st.sidebar:
    st.caption("🔐 Inline Diagnostics")
    st.write("st.secrets.OPENAI_API_KEY:", _mask(secret_key))
    st.write("env OPENAI_API_KEY:", _mask(env_key))

# If env still holds a project key, neutralize it
if env_key.startswith("sk-proj-"):
    try:
        del os.environ["OPENAI_API_KEY"]
    except Exception:
        pass

# Force all downstream code paths to the **secrets** value
if secret_key:
    os.environ["OPENAI_API_KEY"] = secret_key
# ----- END INLINE DIAGNOSTICS + FORCE FIX -----

import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Load .env locally
load_dotenv()

# --- Robust key handling & validator ---
def _sanitize(s: str | None) -> str:
    return (s or "").strip().replace("\r", "").replace("\n", "")

def _put_env_if_nonempty(name: str, value: str):
    v = _sanitize(value)
    if v:
        os.environ[name] = v

# Pull from Streamlit secrets first (cloud), then fall back to .env
st_openai = None
st_polygon = None
try:
    if "OPENAI_API_KEY" in st.secrets:
        st_openai = str(st.secrets["OPENAI_API_KEY"])
    if "POLYGON_API_KEY" in st.secrets:
        st_polygon = str(st.secrets["POLYGON_API_KEY"])
except Exception:
    pass

# Only set env if the secret is non-empty (avoid overwriting good values)
_put_env_if_nonempty("OPENAI_API_KEY", st_openai or os.getenv("OPENAI_API_KEY", ""))
_put_env_if_nonempty("POLYGON_API_KEY", st_polygon or os.getenv("POLYGON_API_KEY", ""))

OPENAI_KEY = _sanitize(os.getenv("OPENAI_API_KEY", ""))
POLYGON_KEY = _sanitize(os.getenv("POLYGON_API_KEY", ""))

def _mask(k: str) -> str:
    if not k:
        return "(none)"
    if len(k) <= 10:
        return "****"
    return f"{k[:6]}…{k[-4:]}"

st.set_page_config(page_title="Market AI — Chat + Forecast", layout="wide")
st.title("💬📈 Market AI — Chat + Forecasts")

# Hard fail fast if a project key is used
if OPENAI_KEY.startswith("sk-proj-"):
    st.error(
        "⚠️ Detected an **OpenAI Project key** (`sk-proj-…`). "
        "This build requires a **personal secret key** that starts with `sk-`.\n\n"
        "Go to https://platform.openai.com/api-keys, switch to **Personal** (top-left), "
        "click **Create new secret key**, then paste it in **Settings → Secrets** as:\n\n"
        '```toml\nOPENAI_API_KEY = "sk-..."\nPOLYGON_API_KEY = "your-polygon-key"\n```'
    )
    st.stop()

from tools import get_quote, forecast, news_sentiment, screen_top_movers, default_universe, _download_yf
from llm import respond

tab_chat, tab_analysis = st.tabs(["💬 Chat", "📈 Analysis"])

with st.sidebar:
    st.subheader("API Health Check")
    if st.button("Test OpenAI"):
        try:
            from openai import OpenAI
            key = OPENAI_KEY
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
            key = POLYGON_KEY
            r = requests.get(f"https://api.polygon.io/v3/reference/tickers?limit=1&apiKey={key}", timeout=15)
            if r.status_code == 200:
                st.success("Polygon ✅")
            else:
                st.warning(f"Polygon responded with status {r.status_code}")
        except Exception as e:
            st.error(f"Polygon ❌ {e}")

    st.divider()
    st.caption("Key status (masked)")
    st.write(f"OpenAI key: **{_mask(OPENAI_KEY)}**")
    st.write("Type: " + ("Personal ✅" if OPENAI_KEY.startswith("sk-") else ("Project ❌" if OPENAI_KEY.startswith("sk-proj-") else "Missing ❌")))
    st.write(f"Polygon key: **{_mask(POLYGON_KEY)}**")

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
