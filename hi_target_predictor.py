
# modules/hi_target_predictor.py
import pandas as pd
from .strategy import RiskManagedStrategy

def run_hi_target_strategy(ohlcv: pd.DataFrame, horizon_days=5, price_col="close"):
    strat = RiskManagedStrategy(
        vol_target_daily=0.015,   # slightly higher aggression than default
        max_leverage=2.5,         # careful with >2.5
        stop_loss_pct=0.02,
        take_profit_pct=0.04,     # go for bigger wins
        kelly_cap=0.6
    )
    bt_df, summary = strat.backtest(ohlcv, price_col=price_col)
    return bt_df, summary
