
# 5%-Target Variant (Aggressive) — with Leverage, SL/TP, Auto-Backtest

This bundle upgrades your app to AIM for larger moves using:
- Multi-feature signal (RSI, MACD, Bollinger %B, ATR, momentum z-scores)
- Confidence-weighted sizing + volatility targeting
- Leverage cap + Kelly cap
- Hard Stop-Loss / Take-Profit
- Auto-backtest script on free Alpha Vantage 1-min data

## Files
- modules/signal.py — feature builders
- modules/strategy.py — risk-managed strategy (sizing, SL/TP, vol-target)
- modules/hi_target_predictor.py — pre-tuned "5%-target" settings
- modules/finnhub_ws.py — free real-time (Finnhub WS)
- modules/alphavantage_polling.py — free polling (Alpha Vantage)
- notebooks/backtest_last_year.py — quick backtest script

## Install (requirements.txt)
pandas
numpy
requests
websockets

## Add Secrets (Streamlit → Settings → Secrets)
FINNHUB_API_KEY = "your-finnhub-key"
ALPHAVANTAGE_API_KEY = "your-alphavantage-key"

## Integrate into your app.py
from modules.hi_target_predictor import run_hi_target_strategy

# Assuming you have a `hist` DataFrame with Date + Close:
hist_df = hist.set_index("Date") if "Date" in hist.columns else hist
ohlcv = pd.DataFrame(index=hist_df.index)
ohlcv["close"] = hist_df["Close"].astype(float)
ohlcv["open"] = ohlcv["close"].shift(1).fillna(ohlcv["close"])
ohlcv["high"] = ohlcv[["open","close"]].max(axis=1)
ohlcv["low"]  = ohlcv[["open","close"]].min(axis=1)

bt_df, summary = run_hi_target_strategy(ohlcv, horizon_days=7, price_col="close")
# Display summary and chart in Streamlit as shown earlier.

## Run the auto-backtest (local or cloud shell)
export ALPHAVANTAGE_API_KEY=YOUR_KEY
export BT_SYMBOL=AAPL
python notebooks/backtest_last_year.py

## Notes
- 5% a week consistently is extremely aggressive; not guaranteed.
- Tune params in `hi_target_predictor.py` and re-run backtests.
- Paper-trade before risking capital.
