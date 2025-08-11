
# Market AI — Dual Mode (Chat + Analysis)

- ChatGPT‑style chat (OpenAI) with forecasting, screening, and news sentiment
- Analysis tab with line chart + forecast table + sentiment
- Confidence intervals and prob_up in text
- ASX + US universes
- Health Check buttons for OpenAI and Polygon

## Run locally
```
cp .env.example .env   # add your keys
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Streamlit Cloud
- Upload repo → main file: `streamlit_app.py`
- Settings → Secrets:
```
OPENAI_API_KEY = "sk-..."
POLYGON_API_KEY = "your-polygon-key"
```
- Restart app after saving secrets
