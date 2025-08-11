
# Market AI — Dual Mode HOTFIX (prevents 401 after first call)

Fixes:
- Sanitizes OPENAI_API_KEY (strips newlines/spaces)
- Uses Secrets only if non-empty (won’t overwrite a good env with empty)
- Gentle OpenAI health check (tiny chat ping)
- Guarded OpenAI client with friendly error messages

Features:
- ChatGPT-style chat (OpenAI) with forecasting/screening/news sentiment
- Analysis tab with line chart + forecast table + sentiment
- Confidence intervals + prob_up in text
- ASX + US universes

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
