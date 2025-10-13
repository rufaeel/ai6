
# modules/signal.py
import numpy as np
import pandas as pd

def _ema(x, span):
    return x.ewm(span=span, adjust=False).mean()

def rsi(close, length=14):
    delta = close.diff()
    up = delta.clip(lower=0).rolling(length).mean()
    down = (-delta.clip(upper=0)).rolling(length).mean()
    rs = up / (down + 1e-12)
    return 100 - (100 / (1 + rs))

def macd(close, fast=12, slow=26, signal=9):
    macd_line = _ema(close, fast) - _ema(close, slow)
    signal_line = _ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def bollinger(close, length=20, mult=2):
    ma = close.rolling(length).mean()
    sd = close.rolling(length).std()
    upper = ma + mult*sd
    lower = ma - mult*sd
    bbp = (close - lower) / (upper - lower + 1e-12)
    width = (upper - lower) / (ma + 1e-12)
    return ma, upper, lower, bbp, width

def atr(high, low, close, length=14):
    prev_close = close.shift(1)
    tr = pd.concat([
        (high-low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(length).mean()

def build_features(df, price_col="close"):
    x = df.copy().sort_index()
    c = x[price_col].astype(float)
    h = x.get("high", c)
    l = x.get("low", c)

    x["ret1"] = c.pct_change()
    x["ret5"] = c.pct_change(5)
    x["ret20"] = c.pct_change(20)

    x["rsi14"] = rsi(c, 14)
    macd_line, macd_sig, macd_hist = macd(c)
    x["macd"] = macd_line
    x["macd_sig"] = macd_sig
    x["macd_hist"] = macd_hist

    ma, up, lo, bbp, width = bollinger(c, 20, 2)
    x["bbp"] = bbp
    x["bb_width"] = width

    x["atr14"] = atr(h, l, c, 14)
    x["vol10"] = x["ret1"].rolling(10).std()
    x["vol20"] = x["ret1"].rolling(20).std()

    x["z_mom5"] = (x["ret5"] - x["ret5"].rolling(100).mean()) / (x["ret5"].rolling(100).std() + 1e-9)
    x["z_bbp"] = (x["bbp"] - x["bbp"].rolling(100).mean()) / (x["bbp"].rolling(100).std() + 1e-9)
    x = x.dropna()
    return x

def confidence_score(feat: pd.DataFrame):
    score = 0.0
    score += np.tanh((feat["z_mom5"]).fillna(0)) * 0.35
    score += np.tanh((feat["macd_hist"]).fillna(0) * 5) * 0.25
    score += np.tanh((0.5 - feat["bb_width"].rank(pct=True))*3) * 0.15
    score += np.tanh(((feat["rsi14"]-50)/10)) * 0.15
    pen = np.tanh((feat["vol10"]/(feat["vol20"]+1e-9))*3 - 1)
    score -= pen.clip(lower=0) * 0.20
    conf = (np.tanh(score)*0.5 + 0.5)
    return conf.clip(0,1)
