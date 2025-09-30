
# Market AI — Dual Mode (KeyGuard Build)

**What’s new (anti-401):**
- Rejects `sk-proj-...` keys at startup with a clear message.
- Sanitizes keys (trims spaces/newlines).
- Sidebar shows masked key status & type.
- Gentle OpenAI health check.

**Features:**
- ChatGPT-style chat for markets (OpenAI).
- ASX + US tickers, forecasts with confidence intervals.
- Polygon news sentiment.
- Analysis tab with chart + forecast table.

## Deploy on Streamlit Cloud
1. Upload this repo. Main file: `streamlit_app.py`
2. **Settings → Secrets** (TOML):
```
OPENAI_API_KEY = "sk-your-personal-key"
POLYGON_API_KEY = "your-polygon-key"
```
3. Save → **Restart** app.

## Run locally
```
cp .env.example .env   # paste your keys without quotes
pip install -r requirements.txt
streamlit run streamlit_app.py
```
