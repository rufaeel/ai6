import os, json, re
from typing import Dict, Any
from openai import OpenAI

SYSTEM_PROMPT = """You are MarketAI, a careful financial assistant.
- Always include probabilities and confidence intervals if available.
- You can call tools to fetch quotes, forecasts, news sentiment, or screen top movers.
- If the user asks 'which will rise most', use screening with a short, readable table.
- Never promise 100% accuracy; use probabilistic language.
- If a ticker looks invalid, ask for clarification.
Return concise, direct answers.
"""

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def route_intent(user_text: str) -> Dict[str,str]:
    t = user_text.lower()
    if "top" in t and ("rise" in t or "gainer" in t or "shoot" in t):
        # detect horizon
        if "today" in t or "1d" in t:
            return {"action":"screen", "horizon":"1d"}
        if "month" in t:
            return {"action":"screen", "horizon":"30d"}
        return {"action":"screen", "horizon":"7d"}
    if "forecast" in t or "predict" in t or "price target" in t:
        # grab ticker-ish token
        m = re.findall(r"[A-Za-z]{1,5}\.?[A-Za-z]{0,3}\.?(AX)?", user_text)
        ticker = m[-1] if m else "AAPL"
        return {"action":"forecast", "ticker": ticker, "horizon":"7d"}
    if "news" in t or "sentiment" in t:
        m = re.findall(r"[A-Za-z]{1,5}\.?[A-Za-z]{0,3}\.?(AX)?", user_text)
        ticker = m[-1] if m else "AAPL"
        return {"action":"news", "ticker": ticker}
    if "quote" in t or "price" in t:
        m = re.findall(r"[A-Za-z]{1,5}\.?[A-Za-z]{0,3}\.?(AX)?", user_text)
        ticker = m[-1] if m else "AAPL"
        return {"action":"quote", "ticker": ticker}
    # fallback to chat
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
    # Fallback chat via LLM
    msg = [{"role":"system","content":SYSTEM_PROMPT},
           {"role":"user","content":user_text}]
    resp = client.chat.completions.create(model="gpt-4o-mini", messages=msg)
    return resp.choices[0].message.content.strip()
