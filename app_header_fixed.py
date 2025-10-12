
# --- Drop-in header for your Streamlit Stock AI app ---
# Replace the top of your app.py with everything in this file down to the '--- END HEADER ---' line.
import os
import streamlit as st
import requests
from openai import OpenAI

# ---------- Secrets & Env handling ----------
def _get_secret(name: str, default: str | None = None) -> str | None:
    # Works on Streamlit Cloud and locally with .streamlit/secrets.toml; falls back to environment
    try:
        return st.secrets[name]
    except Exception:
        return os.getenv(name, default)

OPENAI_API_KEY = _get_secret("OPENAI_API_KEY")
POLYGON_API_KEY = _get_secret("POLYGON_API_KEY")

# Basic validation: we need a *personal* OpenAI key, not a project key.
if not OPENAI_API_KEY:
    st.stop()
    raise RuntimeError("Missing OPENAI_API_KEY. Add it in Streamlit Secrets or your environment.")
if OPENAI_API_KEY.startswith("sk-proj-"):
    st.error("⚠️ Detected an OpenAI *Project* key (sk-proj-…). Use a PERSONAL key that starts with 'sk-'.")
    st.stop()

if not POLYGON_API_KEY:
    st.warning("No POLYGON_API_KEY set. Polygon calls will fail until you add it.")

# ---------- OpenAI & Polygon clients ----------
# OpenAI official client (recommended pattern)
oai = OpenAI(api_key=OPENAI_API_KEY)

# Simple Polygon helper
def polygon_get(path: str, params: dict | None = None, timeout: int = 30):
    base = "https://api.polygon.io"
    params = params.copy() if params else {}
    params["apiKey"] = POLYGON_API_KEY
    resp = requests.get(f"{base}{path}", params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()

# ---------- Optional sanity checks (toggle in sidebar) ----------
with st.sidebar:
    run_checks = st.toggle("Run API self-test", value=False, help="Quickly verify both APIs are reachable.")

if run_checks:
    st.info("Running self-test…")
    # OpenAI: list models (cheap call)
    try:
        models = oai.models.list()
        st.success(f"OpenAI OK · {len(models.data)} models visible. Example: {models.data[0].id if models.data else 'n/a'}")
    except Exception as e:
        st.error(f"OpenAI error: {e}")

    # Polygon: previous close for AAPL
    if POLYGON_API_KEY:
        try:
            prev = polygon_get("/v2/aggs/ticker/AAPL/prev", {"adjusted": "true"})
            st.success("Polygon OK · Sample response keys: " + ", ".join(list(prev.keys())[:5]))
        except Exception as e:
            st.error(f"Polygon error: {e}")
    else:
        st.warning("Polygon skipped (no key).")

# --- END HEADER ---
