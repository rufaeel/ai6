
import os
import re
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from modules.hi_target_predictor import run_hi_target_strategy
import pandas as pd
from intent_hotfix_top_gainers.tools_additions import handle_top_gainer_query
from modules.predictor import predict_direction
from tools import _download_yf
import re


# Optional: still load .env for local dev of NON-secrets like POLYGON if you want
load_dotenv()

def _sanitize(s: str | None) -> str:
    return (s or "").strip().replace("\r", "").replace("\n", "")

def _mask(k: str | None) -> str:
    if not k:
        return "(none)"
    k = str(k)
    return k[:6] + "…" + k[-6:] if len(k) > 12 else "****"

def _is_project_key(k: str | None) -> bool:
    return bool(k) and str(k).startswith("sk-proj-")

def _is_personal_key(k: str | None) -> bool:
    return bool(k) and str(k).startswith("sk-") and not str(k).startswith("sk-proj-")

# --------- STRICT: get keys from Streamlit Secrets ONLY ----------
st_openai = None
st_polygon = None
try:
    st_openai = str(st.secrets.get("OPENAI_API_KEY", "")).strip()
    st_polygon = str(st.secrets.get("POLYGON_API_KEY", "")).strip()
except Exception:
    # On Streamlit Cloud, st.secrets is always available if set in Settings → Secrets
    pass

# Hard-require OPENAI key from secrets
if not _is_personal_key(st_openai):
    st.error(
        "Missing or invalid **OPENAI_API_KEY** in **Streamlit Secrets**.\n\n"
        "- Go to your app → **Settings → Secrets** and paste:\n"
        '```toml\nOPENAI_API_KEY = "sk-...your personal key..."\nPOLYGON_API_KEY = "your-polygon-key"\n```'
        "- Make sure it **starts with `sk-` and NOT `sk-proj-`**.\n"
        "- If you previously set **Environment Variables** with `OPENAI_API_KEY`, clear them in **Settings → Advanced**."
    )
    st.stop()

# Neutralize any conflicting env var holding sk-proj-...
existing_env = os.getenv("OPENAI_API_KEY", "")
if _is_project_key(existing_env):
    try:
        del os.environ["OPENAI_API_KEY"]
    except Exception:
        pass

# Force all downstream code (including any legacy libs) to the good value
os.environ["OPENAI_API_KEY"] = st_openai

# Optional: polygon can come from secrets or env (.env for local dev)
polygon_key = st_polygon or _sanitize(os.getenv("POLYGON_API_KEY", ""))

OPENAI_KEY = _sanitize(os.environ.get("OPENAI_API_KEY", ""))
POLYGON_KEY = polygon_key

st.set_page_config(page_title="Market AI — Chat + Forecast", layout="wide")
st.title("💬📈 Market AI — Chat + Forecasts")

# Final guardrail (should never trigger now unless someone pasted a proj key into secrets)
if _is_project_key(OPENAI_KEY):
    st.error(
        "⚠️ Detected an **OpenAI Project key** (`sk-proj-…`). "
        "This build requires a **personal** key that starts with `sk-`.\n\n"
        "Create a new personal key and put it in **Settings → Secrets** as:\n"
        '```toml\nOPENAI_API_KEY = "sk-..."\nPOLYGON_API_KEY = "your-polygon-key"\n```'
    )
    st.stop()

# Sidebar: health + correct type label
with st.sidebar:
    st.subheader("API Health Check")
    if st.button("Test OpenAI"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_KEY)
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
            r = requests.get(
                "https://api.polygon.io/v3/reference/tickers",
                params={"limit": 1, "apiKey": POLYGON_KEY},
                timeout=15
            )
            st.success("Polygon ✅" if r.status_code == 200 else f"Polygon responded {r.status_code}")
        except Exception as e:
            st.error(f"Polygon ❌ {e}")

    st.divider()
    st.caption("Key status (masked)")
    st.write(f"OpenAI key: **{_mask(OPENAI_KEY)}**")
    # Fix the label logic: check project BEFORE personal
    if _is_project_key(OPENAI_KEY):
        st.write("Type: Project ❌")
    elif _is_personal_key(OPENAI_KEY):
        st.write("Type: Personal ✅")
    else:
        st.write("Type: Missing/Invalid ❌")
    st.write(f"Polygon key: **{_mask(POLYGON_KEY)}**")

# ------------------- ORIGINAL APP CONTENT BELOW -------------------
from tools import get_quote, forecast, news_sentiment, screen_top_movers, default_universe, _download_yf
from llm import respond

tab_chat, tab_analysis = st.tabs(["💬 Chat", "📈 Analysis"])

with st.sidebar:
    # (Sidebar content already rendered above; keep layout consistent)
    pass

with tab_chat:
    st.caption("Ask things like ‘Forecast CBA.AX 7d’, ‘Top stocks this week’, or ‘News TSLA’.")
    if "history" not in st.session_state:
        st.session_state.history = []
    for role, content in st.session_state.history:
        st.chat_message(role).markdown(content)
    user_text = st.chat_input("Ask a question about stocks, crypto, news, or forecasts…")
    if user_text:
        from intent_hotfix_top_gainers.tools_additions import handle_highest_riser_intent
from modules.predictor import predict_direction
from tools import _download_yf
import re

user_text = st.chat_input("Ask a question about stocks…")
if user_text:
    st.session_state.history.append(("user", user_text))
    st.chat_message("user").write(user_text)

    # 💡 Add this block just below the st.chat_message("user") line
    if re.search(r"(highest\\s+riser|top\\s+gainer|rise\\s+highest\\s+today|which\\s+stock\\s+will\\s+rise\\s+most\\s+today)", user_text, re.I):
        answer = handle_highest_riser_intent(_download_yf, predict_direction, limit=10, horizon_days=7)
        st.session_state.history.append(("assistant", answer))
        st.chat_message("assistant").markdown(answer)
        st.stop()  # stops here so the regular respond() doesn’t run

    # your normal chat fallback logic
    answer = respond(user_text, {...})
    st.session_state.history.append(("assistant", answer))
    st.chat_message("assistant").markdown(answer)

        # Intent: predict highest riser today / top gainer today / biggest mover
text = (user_text or "").strip()
if re.search(r"(highest\s+riser|top\s+gainer|biggest\s+mover)", text, re.I):
    answer = handle_top_gainer_query(_download_yf, predict_direction, limit=10, horizon_days=7)
    st.session_state.history.append(("assistant", answer))
    st.chat_message("assistant").markdown(answer)
    st.stop()  # prevents sending to the general LLM handler

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
        # --- Aggressive Strategy (5%-target backtest) ---
# Convert your historical data (hist) into OHLCV format
hist_df = hist.set_index("Date") if "Date" in hist.columns else hist
ohlcv = pd.DataFrame(index=hist_df.index)
ohlcv["close"] = hist_df["Close"].astype(float)
ohlcv["open"]  = ohlcv["close"].shift(1).fillna(ohlcv["close"])
ohlcv["high"]  = ohlcv[["open","close"]].max(axis=1)
ohlcv["low"]   = ohlcv[["open","close"]].min(axis=1)

# Run the high-target strategy (aiming for larger moves)
bt_df, summary = run_hi_target_strategy(ohlcv, horizon_days=7, price_col="close")

st.subheader("Aggressive Strategy (larger-move targeting)")
st.write(
    f"Bars: {summary['bars']:,} | Final equity: {summary['final_equity']:.2f}x | "
    f"Weekly mean: {summary['weekly_mean']*100:.2f}% | "
    f"Median: {summary['weekly_median']*100:.2f}% | "
    f"5–95%: {summary['weekly_p05']*100:.2f}% → {summary['weekly_p95']*100:.2f}% | "
    f"Hit rate: {summary['hit_rate']*100:.1f}% | Sharpe(d): {summary['sharpe_daily']:.2f}"
)
st.line_chart(bt_df["equity"])


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
