
# modules/strategy.py
import numpy as np
import pandas as pd
from .signal import build_features, confidence_score

class RiskManagedStrategy:
    def __init__(
        self,
        vol_target_daily=0.012,
        max_leverage=2.0,
        stop_loss_pct=0.02,
        take_profit_pct=0.03,
        kelly_cap=0.5
    ):
        self.vol_target_daily = vol_target_daily
        self.max_leverage = max_leverage
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.kelly_cap = kelly_cap

    @staticmethod
    def _kelly_fraction(p, r=1.2):
        return (p - (1 - p) / (r + 1e-9))

    def _size_from_conf_and_vol(self, conf, realized_vol):
        base = conf * self.max_leverage
        scale = (self.vol_target_daily / realized_vol) if (realized_vol > 1e-6) else 1.0
        return max(0.0, min(base * scale, self.max_leverage))

    def generate_positions(self, prices: pd.Series, features: pd.DataFrame):
        idx = features.index.intersection(prices.index)
        p = prices.loc[idx]
        f = features.loc[idx]
        conf = confidence_score(f)
        prob_up = (conf * 0.5 + 0.5).clip(0.5, 0.99)
        realized_vol = f["vol20"].fillna(f["vol10"]).fillna(0.01)
        size = [self._size_from_conf_and_vol(float(c), float(v)) for c, v in zip(conf, realized_vol)]
        kelly = [max(0.0, min(1.0, self._kelly_fraction(float(pu), r=1.2))) for pu in prob_up]
        size = np.minimum(size, (np.array(kelly) * self.kelly_cap) * self.max_leverage + 1e-6)
        out = pd.DataFrame({"close": p, "prob_up": prob_up.values, "conf": conf.values, "size": size}, index=p.index)
        return out

    def backtest(self, df_ohlcv: pd.DataFrame, price_col="close"):
        data = df_ohlcv.copy().sort_index()
        f = build_features(data, price_col)
        positions = self.generate_positions(data[price_col], f)

        o = data.get("open", data[price_col])
        h = data.get("high", data[price_col])
        l = data.get("low", data[price_col])
        c = data[price_col]

        df = positions.join(pd.DataFrame({"open":o, "high":h, "low":l, "close":c}), how="inner")
        df["ret_bar"] = df["close"].pct_change().fillna(0)

        prev_close = df["close"].shift(1)
        up_hit = (df["high"] >= prev_close * (1 + self.take_profit_pct))
        dn_hit = (df["low"]  <= prev_close * (1 - self.stop_loss_pct))

        realized = df["ret_bar"].copy()
        realized[up_hit] = self.take_profit_pct
        realized[dn_hit] = -self.stop_loss_pct

        df["pnl"] = df["size"].shift(1).fillna(0) * realized
        df["equity"] = (1 + df["pnl"]).cumprod()

        wk = df["equity"].resample("W-FRI").last().pct_change().dropna()
        summary = {
            "bars": int(df.shape[0]),
            "final_equity": float(df["equity"].iloc[-1]),
            "weekly_mean": float(wk.mean() if len(wk)>0 else 0.0),
            "weekly_median": float(wk.median() if len(wk)>0 else 0.0),
            "weekly_p05": float(wk.quantile(0.05) if len(wk)>0 else 0.0),
            "weekly_p95": float(wk.quantile(0.95) if len(wk)>0 else 0.0),
            "sharpe_daily": float((np.sqrt(252) * (df["pnl"].mean() / (df["pnl"].std() + 1e-12))) if df["pnl"].std()>0 else 0.0),
            "hit_rate": float((df["pnl"] > 0).mean() if len(df)>0 else 0.0)
        }
        return df, summary
