
# Market AI — Fixed App (Personal OpenAI Key)

This bundle contains a hardened `app.py` that:
- Reads `OPENAI_API_KEY` **only** from Streamlit **Secrets**.
- Deletes any lingering `sk-proj-…` value from `env` to prevent accidental use.
- Forces all downstream code paths to the correct **personal** key (`sk-…`).
- Shows masked key values in the sidebar and includes a one-click OpenAI test.

## Setup

### 1) Add Secrets (local or cloud)
Create `.streamlit/secrets.toml` locally **or** use Streamlit Cloud → Settings → Secrets:

```toml
OPENAI_API_KEY = "sk-...your personal key (not sk-proj)..."
POLYGON_API_KEY = "your-polygon-key"
```

### 2) Remove conflicting environment variables
In Streamlit Cloud → Settings → Advanced → Environment variables: **delete** any `OPENAI_API_KEY` there.
(Keep only the Secrets above.)

### 3) Run locally
```bash
pip install -r requirements.txt  # ensure streamlit, openai, requests, pandas, python-dotenv are installed
streamlit run app.py
```

### 4) Diagnostics (optional)
Run
```bash
streamlit run key_diagnostics.py
```
to see what key your app actually reads (masked).

