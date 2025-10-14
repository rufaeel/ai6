
# intent_hotfix_top_gainers/tools_additions.py
import os, re, requests, pandas as pd
from typing import List, Dict

POLY_KEY = os.getenv("POLYGON_API_KEY", "")
AV_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")

def top_gainers_today(limit: int = 10) -> pd.DataFrame:
    items = []
    if POLY_KEY:
        try:
            url = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/gainers"
            r = requests.get(url, params={"apiKey": POLY_KEY}, timeout=20)
            r.raise_for_status()
            data = r.json()
            for it in (data.get("tickers") or [])[: max(1, limit)]:
                last = it.get("lastTrade") or {}
                price = last.get("p") if isinstance(last, dict) else None
                items.append({
                    "symbol": it.get("ticker"),
                    "price": price,
                    "change_pct": it.get("todaysChangePerc"),
                    "source": "polygon"
                })
        except Exception:
            items = []

    if not items:
        if not AV_KEY:
            raise RuntimeError("No data source available: set POLYGON_API_KEY or ALPHAVANTAGE_API_KEY in Secrets.")
        url = "https://www.alphavantage.co/query"
        r = requests.get(url, params={"function":"TOP_GAINERS_LOSERS","apikey":AV_KEY}, timeout=20)
        r.raise_for_status()
        data = r.json()
        tg = data.get("top_gainers", [])[: max(1, limit)]
        for g in tg:
            pct_txt = (g.get("change_percentage") or "").replace("%","").replace("+","")
            try:
                pct_val = float(pct_txt)
            except Exception:
                pct_val = None
            try:
                price_val = float(g.get("price") or 0)
            except Exception:
                price_val = None
            items.append({
                "symbol": g.get("ticker"),
                "price": price_val,
                "change_pct": pct_val,
                "source": "alphavantage"
            })
    return pd.DataFrame(items)

def rank_symbols_by_model(symbols: List[str], download_hist_fn, predictor_fn, horizon_days: int = 7) -> pd.DataFrame:
    rows = []
    for sym in symbols:
        try:
            hist = download_hist_fn(sym, 365)
            if hist is None or len(hist) == 0:
                continue
            df = hist.set_index("Date") if "Date" in hist.columns else hist
            if "Close" not in df.columns or df["Close"].isna().all():
                continue
            res = predictor_fn(df[["Close"]], horizon_days=horizon_days, price_col="Close")
            if res.get("ok"):
                rows.append({
                    "symbol": sym,
                    "prob_up": float(res["prob_up"]),
                    "expected_return_pct": float(res["expected_return_pct"]),
                    "score": float(res["score"])
                })
        except Exception:
            continue
    import pandas as pd
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["expected_return_pct","prob_up"], ascending=[False, False]).reset_index(drop=True)

def handle_top_gainer_query(download_hist_fn, predictor_fn, limit: int = 10, horizon_days: int = 7) -> str:
    gainers = top_gainers_today(limit=limit)
    if gainers is None or gainers.empty:
        return "I couldn't find gainers right now. Try again later."
    ranked = rank_symbols_by_model(gainers["symbol"].tolist(), download_hist_fn, predictor_fn, horizon_days=horizon_days)
    if ranked is None or ranked.empty:
        lines = [f"**{r.symbol}** {r.change_pct:+.2f}% (price {r.price})" for r in gainers.head(5).itertuples()]
        return "Top gainers (raw):\n\n" + "\n".join(["- "+x for x in lines])
    merged = ranked.merge(gainers[["symbol","price","change_pct","source"]], on="symbol", how="left")
    top_pick = merged.iloc[0]
    reply = [
        f"**Model pick (next {horizon_days}d)**: **{top_pick['symbol']}**",
        f"- Prob(up): **{top_pick['prob_up']:.2f}**",
        f"- Expected return: **{top_pick['expected_return_pct']:.2f}%**",
        f"- Today change: {float(top_pick.get('change_pct') or 0):+.2f}%  |  Price: {top_pick.get('price')}  |  Source: {top_pick.get('source')}",
        "",
        "Other candidates:",
    ]
    for _, r in merged.head(5).iterrows():
        reply.append(f"- {r['symbol']}: exp {r['expected_return_pct']:.2f}% | prob_up {r['prob_up']:.2f} | today {float(r.get('change_pct') or 0):+.2f}%")
    return "\n".join(reply)
