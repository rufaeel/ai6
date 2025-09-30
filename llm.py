
import os
import re
from typing import Dict
from openai import OpenAI

def _get_openai_key() -> str:
    key = None
    try:
        import streamlit as st
        if "OPENAI_API_KEY" in st.secrets:
            key = st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    if not key:
        key = os.getenv("OPENAI_API_KEY", "")
    key = (key or "").strip().replace("\r", "").replace("\n", "")
    # Reject project keys explicitly so the user sees a clear message
    if key.startswith("sk-proj-"):
        return ""
    return key

SYSTEM_PROMPT = (
    "You are MarketAI, a careful financial assistant. "
    "Use tools to fetch quotes, forecasts (with confidence intervals), news sentiment, "
    "or screen top movers. Always include uncertainty. Be concise. "
    "Never claim 100% accuracy. If a ticker seems invalid, ask for clarification."
)

def route_intent(user_text: str) -> Dict[str, str]:
    t = user_text.lower()
    if "top" in t and ("rise" in t or "gainer" in t or "shoot" in t):
        if "today" in t or "1d" in t:
            return {"action": "screen", "horizon": "1d"}
        if "month" in t:
            return {"action": "screen", "horizon": "30d"}
        return {"action": "screen", "horizon": "7d"}
    if "forecast" in t or "predict" in t or "price target" in t:
        m = re.findall(r"[A-Za-z]{1,5}(?:\.[A-Za-z]{1,3})?(?:\.AX)?", user_text)
        return {"action": "forecast", "ticker": (m[-1] if m else "AAPL"), "horizon": "7d"}
    if "news" in t or "sentiment" in t:
        m = re.findall(r"[A-Za-z]{1,5}(?:\.[A-Za-z]{1,3})?(?:\.AX)?", user_text)
        return {"action": "news", "ticker": (m[-1] if m else "AAPL")}
    if "quote" in t or "price" in t:
        m = re.findall(r"[A-Za-z]{1,5}(?:\.[A-Za-z]{1,3})?(?:\.AX)?", user_text)
        return {"action": "quote", "ticker": (m[-1] if m else "AAPL")}
    return {"action": "chat"}

def _chat_llm(user_text: str) -> str:
    key = _get_openai_key()
    if not key:
        return (
            "❗ **OPENAI_API_KEY missing or invalid.**\n\n"
            "- Make sure you created a **personal key** (starts with `sk-`, not `sk-proj-`).\n"
            "- In Streamlit Cloud → **Settings → Secrets** use TOML:\n"
            '```toml\nOPENAI_API_KEY = "sk-..."\nPOLYGON_API_KEY = "your-polygon-key"\n```'
        )
    try:
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            max_tokens=500,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"OpenAI error: {e}"

def respond(user_text: str, toolkit) -> str:
    route = route_intent(user_text)
    act = route["action"]

    if act == "forecast":
        fc = toolkit["forecast"](route["ticker"], route.get("horizon", "7d"))
        if not fc.get("ok"):
            return f"Couldn't forecast {route['ticker']}: {fc.get('error')}"
        lines = []
        lines.append(f"**{fc['ticker']} – {fc['horizon_days']}d forecast**")
        lines.append(f"Current: {fc['current_price']:.4f}")
        lines.append(f"Expected return: {fc['expected_return_pct']:.2f}%")
        lines.append(f"Prob(up): {fc['prob_up']:.2f}")
        lines.append("")
        lines.append("**Confidence interval (daily)**")
        for row in fc["forecast"]:
            lines.append(f"- {row['date']}: {row['lower']:.2f} → {row['pred']:.2f} → {row['upper']:.2f}")
        return "\n".join(lines)

    if act == "news":
        ns = toolkit["news_sentiment"](route["ticker"])
        if not ns.get("ok"):
            return "Couldn't fetch news sentiment."
        out = [f"**News sentiment for {route['ticker']}**", f"Avg sentiment: {ns['avg_sentiment']}"]
        for item in ns["items"][:5]:
            out.append(f"- {item['sentiment']:+.2f} {item['title']}")
        return "\n".join(out)

    if act == "screen":
        uni = toolkit["default_universe"]("mixed")
        rows = toolkit["screen_top_movers"](uni, route["horizon"])
        if not rows:
            return "No forecasts available right now."
        header = (
            "| Ticker | Current | Expected % | Prob Up |\n"
            "|---|---:|---:|---:|"
        )
        body_lines = [
            f"| {r['Ticker']} | {r['Current']:.2f} | {r['Expected %']:.2f}% | {r['Prob Up']:.2f} |"
            for r in rows[:5]
        ]
        table_md = header + "\n" + "\n".join(body_lines)
        return (
            f"**Top candidates ({route['horizon']})**\n\n"
            f"{table_md}\n\n"
            f"_Note: Estimates, not guarantees._"
        )

    if act == "quote":
        q = toolkit["get_quote"](route["ticker"])
        if not q.get("ok"):
            return f"Couldn't fetch quote for {route['ticker']}."
        return f"**{route['ticker']}** price: {q['price']:.4f} ({q['day_change_pct']:+.2f}% today)"

    return _chat_llm(user_text)
