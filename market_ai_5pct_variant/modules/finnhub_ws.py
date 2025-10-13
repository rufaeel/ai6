
# modules/finnhub_ws.py
import asyncio, json, threading, time, logging
import websockets

log = logging.getLogger(__name__); log.setLevel(logging.INFO)

class FinnhubWS:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._subs = set()
        self._cb = None
        self._stop = False
        self._thread = None

    def subscribe(self, *symbols):
        for s in symbols: self._subs.add(s.upper())
    def set_callback(self, fn): self._cb = fn
    def is_running(self): return self._thread is not None and self._thread.is_alive()

    async def _run_once(self):
        url = "wss://ws.finnhub.io?token=" + self.api_key
        async with websockets.connect(url, ping_interval=20) as ws:
            for s in sorted(self._subs):
                await ws.send(json.dumps({"type":"subscribe","symbol": s}))
            while not self._stop:
                msg = await ws.recv()
                try: data = json.loads(msg)
                except Exception: data = msg
                if self._cb:
                    try: self._cb(data)
                    except Exception as e: log.exception("callback error: %s", e)

    def _thread_main(self):
        backoff = 1
        while not self._stop:
            try:
                asyncio.set_event_loop(asyncio.new_event_loop())
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self._run_once()); backoff = 1
            except Exception as e:
                log.warning("Finnhub WS error: %s; reconnect in %ss", e, backoff)
                time.sleep(backoff); backoff = min(backoff*2, 60)

    def start(self):
        if self.is_running(): return
        self._stop = False
        self._thread = threading.Thread(target=self._thread_main, daemon=True); self._thread.start()
    def stop(self): self._stop = True
