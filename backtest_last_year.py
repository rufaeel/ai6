
# notebooks/backtest_last_year.py
# Run: streamlit run or python backtest_last_year.py
import os, sys, pandas as pd, datetime as dt
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from modules.hi_target_predictor import run_hi_target_strategy
from modules.alphavantage_polling import AlphaVantage

SYMBOL = os.getenv("BT_SYMBOL", "AAPL")
APIKEY = os.getenv("ALPHAVANTAGE_API_KEY", "")

def fetch_alpha_intraday_1min(symbol: str, api_key: str) -> pd.DataFrame:
    av = AlphaVantage(api_key)
    data = av.intraday_1min(symbol)
    ts = data.get("Time Series (1min)", {})
    rows = []
    for t, vals in ts.items():
        rows.append({
            "ts": pd.to_datetime(t),
            "open": float(vals["1. open"]),
            "high": float(vals["2. high"]),
            "low": float(vals["3. low"]),
            "close": float(vals["4. close"]),
            "volume": float(vals["5. volume"]),
        })
    df = pd.DataFrame(rows).sort_values("ts").set_index("ts")
    return df

def main():
    if not APIKEY:
        print("Set ALPHAVANTAGE_API_KEY in env. Example: export ALPHAVANTAGE_API_KEY=..."); return
    print(f"Downloading 1min data for {SYMBOL} ...")
    ohlcv = fetch_alpha_intraday_1min(SYMBOL, APIKEY)
    # last 1 year (approx; 1min compact is recent subset; works for demo)
    ohlcv = ohlcv.last('90D')  # AlphaVantage compact is limited; use 90 days for demo
    if ohlcv.empty:
        print("No data returned."); return
    bt_df, summary = run_hi_target_strategy(ohlcv, price_col="close")
    print("Summary:", summary)
    outcsv = f"backtest_{SYMBOL}.csv"
    bt_df.to_csv(outcsv)
    print("Saved per-bar results to", outcsv)

if __name__ == "__main__":
    main()
