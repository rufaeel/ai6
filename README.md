# Market AI — All‑in‑one (OpenAI + Polygon + Forecasts + Sentiment)
Features
- ChatGPT‑style chat UI (OpenAI)
- Live quotes (yfinance)
- Forecasts with confidence intervals & prob_up (Prophet)
- News sentiment via Polygon + VADER
- Screening: “which will rise most” for today/week/month (US + ASX universe)

## Run locally
```
cp .env.example .env   # add your keys
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy on Streamlit Cloud
- Upload repo → New App → main file: `streamlit_app.py`
- Settings → Secrets:
```
OPENAI_API_KEY = "sk-..."
POLYGON_API_KEY = "your-polygon-key"
```
- Deploy & restart

**Note:** Forecasts are probabilistic. Not financial advice.
