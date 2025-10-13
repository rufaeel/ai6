
# modules/alphavantage_polling.py
import time, requests
from functools import lru_cache

class AlphaVantage:
    def __init__(self, api_key: str, timeout: int = 20):
        self.api_key = api_key
        self.timeout = timeout
        self.base = "https://www.alphavantage.co/query"

    def _get(self, params):
        params = dict(params or {})
        params["apikey"] = self.api_key
        r = requests.get(self.base, params=params, timeout=self.timeout)
        if r.status_code == 200 and "Thank you for using Alpha Vantage" in r.text:
            time.sleep(12)
            r = requests.get(self.base, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    @lru_cache(maxsize=1024)
    def global_quote(self, symbol: str):
        return self._get({"function":"GLOBAL_QUOTE", "symbol": symbol})

    def intraday_1min(self, symbol: str):
        return self._get({"function":"TIME_SERIES_INTRADAY","symbol":symbol,"interval":"1min","outputsize":"compact"})
