
import os
import re
from typing import Dict
from openai import OpenAI

SMART_HINTS = [
    "Which US stocks will rise most this week?",
    "Top ASX gainers today",
    "Forecast TSLA 7d with confidence",
    "News sentiment for CBA.AX",
    "Quote NVDA",
]

def _get_openai_key():
    try:
        import streamlit as st
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass
    return os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = (
    "You are MarketAI, a careful financial assistant. "
    "Use tools to fetch quotes, forecasts (with confidence intervals), news sentiment, "
    "or screen top movers. Always include uncertainty. Be concise. "
    "Never claim 100% accuracy. If a ticker seems invalid, ask for clarification."
)

def _parse_horizon(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["today", "1d", "intraday"]):
        return "1d"
    if any(k in t for k in ["month", "30d"]):
        return "30d"
    if any(k in t for k in ["week", "7d", "next week"]):
        return "7d"
    return "7d"

def _parse_market(text: str) -> str:
    t = text.lower()
    if "asx" in t or ".ax" in t:
        return "asx"
    if "us" in t or "nasdaq" in t or "nyse" in t:
        return "us"
    return "mixed"

def _parse_ticker(text: str) -> str:
    # capture US tickers and ASX like CBA.AX
    m = re.findall(r"[A-Za-z]{1,5}(?:\.[A-Za-z]{1,3})?(?:\.AX)?", text)
    return m[-1] if m else ""

def route_intent(user_text: str) -> Dict[str, str]:
    t = user_text.lower()
    ticker = _parse_ticker(user_text)
    horizon = _parse_horizon(user_text)
    market = _parse_market(user_text)

    if any(k in t for k in ["top", "rise", "gainer", "shoot up", "best performer"]):
        return {"action": "screen", "horizon": horizon, "market": market}
    if any(k in t for k in ["forecast", "predict", "price target"]):
        return {"action": "forecast", "ticker": (ticker or "AAPL"), "horizon": horizon}
    if "news" in t or "sentiment" in t:
        return {"action": "news", "ticker": (ticker or "AAPL")}
    if "quote" in t or "price" in t:
        return {"action": "quote", "ticker": (ticker or "AAPL")}
    return {"action": "chat"}

def _chat_llm(user_text: str) -> str:
    key = _get_openai_key()
    if not key:
        return "❗ OPENAI_API_KEY is missing. Add it in Streamlit → Settings → Secrets, or in your .env."
    client = OpenAI(api_key=key)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
    )
    return resp.choices[0].message.content.strip()

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
        uni = toolkit["default_universe"](route.get("market", "mixed"))
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
        market_label = route.get("market", "mixed")
        return (
            f"**Top candidates ({route['horizon']}, {market_label.upper()})**\n\n"
            f"{table_md}\n\n"
            f"_Note: Estimates, not guarantees._"
        )

    if act == "quote":
        q = toolkit["get_quote"](route["ticker"])
        if not q.get("ok"):
            return f"Couldn't fetch quote for {route['ticker']}."
        return f"**{route['ticker']}** price: {q['price']:.4f} ({q['day_change_pct']:+.2f}% today)"

    # Fallback chat
    return _chat_llm(user_text)
