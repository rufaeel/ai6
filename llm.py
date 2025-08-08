
# llm.py
import os, re
from typing import Dict
try:
    import streamlit as st
    _OPENAI = st.secrets.get("OPENAI_API_KEY", None)
except Exception:
    st = None
    _OPENAI = None

# Fallback to environment if not in st.secrets
if not _OPENAI:
    _OPENAI = os.getenv("OPENAI_API_KEY")

from openai import OpenAI

if not _OPENAI:
    # Fail early, but with a clear message (so the app doesn't white-screen)
    raise RuntimeError(
        "Missing OpenAI API key. Set OPENAI_API_KEY in Streamlit Secrets or environment."
    )

client = OpenAI(api_key=_OPENAI)

SYSTEM_PROMPT = """You are MarketAI, a careful financial assistant.
- Always include probabilities and confidence intervals if available.
- You can call tools to fetch quotes, forecasts, news sentiment, or screen top movers.
- If the user asks 'which will rise most', use screening with a short, readable table.
- Never promise 100% accuracy; use probabilistic language.
- If a ticker looks invalid, ask for clarification.
Return concise, direct answers.
"""

def route_intent(user_text: str) -> Dict[str,str]:
    t = user_text.lower()
    import re
    if "top" in t and ("rise" in t or "gainer" in t or "shoot" in t):
        if "today" in t or "1d" in t:
            return {"action":"screen", "horizon":"1d"}
        if "month" in t:
            return {"action":"screen", "horizon":"30d"}
        return {"action":"screen", "horizon":"7d"}
    if "forecast" in t or "predict" in t or "price target" in t:
        m = re.findall(r"[A-Za-z]{1,5}(?:\.[A-Za-z]{1,3})?(?:\.AX)?", user_text)
        ticker = m[-1] if m else "AAPL"
        return {"action":"forecast", "ticker": ticker, "horizon":"7d"}
    if "news" in t or "sentiment" in t:
        m = re.findall(r"[A-Za-z]{1,5}(?:\.[A-Za-z]{1,3})?(?:\.AX)?", user_text)
        ticker = m[-1] if m else "AAPL"
        return {"action":"news", "ticker": ticker}
    if "quote" in t or "price" in t:
        m = re.findall(r"[A-Za-z]{1,5}(?:\.[A-Za-z]{1,3})?(?:\.AX)?", user_text)
        ticker = m[-1] if m else "AAPL"
        return {"action":"quote", "ticker": ticker}
    return {"action":"chat"}

def respond(user_text: str, toolkit) -> str:
    route = route_intent(user_text)
    action = route["action"]
    if action == "forecast":
        fc = toolkit["forecast"](route["ticker"], route.get("horizon","7d"))
        if not fc.get("ok"):
            return f"Couldn't forecast {route['ticker']}: {fc.get('error')}"
        lines = [f"**{fc['ticker']} – {fc['horizon_days']}d forecast**",
                 f"Current: {fc['current_price']:.4f}",
                 f"Expected return: {fc['expected_return_pct']:.2f}%",
                 f"Prob(up): {fc['prob_up']:.2f}"]
        lines.append("\n**Confidence interval (daily)**")
        for row in fc["forecast"]:
            lines.append(f"- {row['date']}: {row['lower']:.2f} → {row['pred']:.2f} → {row['upper']:.2f}")
        return "\n".join(lines)
    if action == "news":
        ns = toolkit["news_sentiment"](route["ticker"])
        if not ns.get("ok"):
            return "Couldn't fetch news sentiment."
        out = [f"**News sentiment for {route['ticker']}**",
               f"Avg sentiment: {ns['avg_sentiment']}"]
        for item in ns["items"][:5]:
            out.append(f"- {item['sentiment']:+.2f} {item['title']}")
        return "\n".join(out)
    if action == "screen":
        uni = toolkit["default_universe"]("mixed")
        df = toolkit["screen_top_movers"](uni, route["horizon"])
        if df.empty:
            return "No forecasts available right now."
        head = df.head(5).to_markdown(index=False)
        return f"**Top candidates ({route['horizon']})**\n\n{head}\n\n_Note: Probabilities and forecasts are estimates, not guarantees._"
    if action == "quote":
        q = toolkit["get_quote"](route["ticker"])
        if not q.get("ok"):
            return f"Couldn't fetch quote for {route['ticker']}."
        return f"**{route['ticker']}** price: {q['price']:.4f} ({q['day_change_pct']:+.2f}% today)"
    # Fallback general chat
    msgs = [{"role":"system","content":SYSTEM_PROMPT},
            {"role":"user","content":user_text}]
    resp = client.chat.completions.create(model="gpt-4o-mini", messages=msgs)
    return resp.choices[0].message.content.strip()
