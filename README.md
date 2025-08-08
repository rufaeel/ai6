# Market AI – ChatGPT‑style Stock/Crypto Forecasts

Public Streamlit app with:
- ChatGPT-like chat for natural questions
- Live quotes, forecasting with confidence intervals (Prophet)
- News sentiment (Polygon + VADER)
- Screening of US + ASX tickers for likely movers

## Quickstart

```bash
git clone <your-repo>
cd <repo>
cp .env.example .env  # then fill in keys
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### Environment
Create a `.env` file:
```
OPENAI_API_KEY=sk-...
POLYGON_API_KEY=...
```

### Deploy (Streamlit Cloud)
- Push to GitHub
- New App → set entrypoint to `streamlit_app.py`
- Add secrets for the two API keys

## Notes
- Forecasts are **probabilistic**; not financial advice.
- Polygon news has best coverage for US; ASX coverage varies.
