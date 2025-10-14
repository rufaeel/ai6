
# --- Robust Header v2: Single Source of Truth for Keys ---
# Paste this at the very top of your app.py (replace the previous header).
import os
import re
import streamlit as st

# Optional compatibility if other files use the legacy 'openai' import
try:
    import openai as openai_legacy
except Exception:
    openai_legacy = None

from openai import OpenAI  # Official modern client

# ------------------ Secrets First (no fallback by default) ------------------
def _read_secret_strict(name: str) -> str | None:
    # Use Streamlit secrets only for the authoritative value.
    try:
        return st.secrets[name]
    except Exception:
        return None

OPENAI_FROM_SECRETS = _read_secret_strict("OPENAI_API_KEY")
POLYGON_FROM_SECRETS = _read_secret_strict("POLYGON_API_KEY")

# ------------------ Detect any conflicting env var ------------------
OPENAI_FROM_ENV = os.getenv("OPENAI_API_KEY")

def _mask(s: str | None) -> str:
    if not s:
        return "NONE"
    return s[:6] + "…" + s[-6:]

# Sidebar: quick status
with st.sidebar:
    st.caption("🔐 Key status (masked)")
    st.write("st.secrets.OPENAI_API_KEY:", _mask(OPENAI_FROM_SECRETS))
    st.write("env OPENAI_API_KEY:", _mask(OPENAI_FROM_ENV))

# ------------------ Validations ------------------
def _is_project_key(k: str) -> bool:
    return bool(k) and k.startswith("sk-proj-")

def _is_personal_key(k: str) -> bool:
    return bool(k) and k.startswith("sk-") and not k.startswith("sk-proj-")

# 1) Must have a personal key in secrets
if not OPENAI_FROM_SECRETS:
    st.error("Missing OPENAI_API_KEY in Streamlit Secrets (.streamlit/secrets.toml or Cloud → Secrets).")
    st.stop()

if not _is_personal_key(OPENAI_FROM_SECRETS):
    st.error("Your OPENAI_API_KEY in secrets does not look like a personal key (must start with 'sk-' and not 'sk-proj-').")
    st.stop()

# 2) Neutralize any project key lingering in environment
if _is_project_key(OPENAI_FROM_ENV):
    # Remove the conflicting env var so legacy code or other libs cannot accidentally read it.
    del os.environ["OPENAI_API_KEY"]

# 3) Force downstream libs to use the secrets value (for any code that relies on env)
os.environ["OPENAI_API_KEY"] = OPENAI_FROM_SECRETS

# 4) Also set legacy openai.api_key if imported elsewhere in your app
if openai_legacy is not None:
    try:
        openai_legacy.api_key = OPENAI_FROM_SECRETS  # legacy style
    except Exception:
        pass

# ------------------ Create the official client ------------------
oai = OpenAI(api_key=OPENAI_FROM_SECRETS)

# ------------------ Polygon helper ------------------
import requests
POLYGON_API_KEY = POLYGON_FROM_SECRETS or os.getenv("POLYGON_API_KEY")
def polygon_get(path: str, params: dict | None = None, timeout: int = 30):
    base = "https://api.polygon.io"
    params = (params or {}).copy()
    params["apiKey"] = POLYGON_API_KEY
    r = requests.get(f"{base}{path}", params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()

# ------------------ Optional self-test ------------------
with st.sidebar:
    run_checks = st.toggle("Run API self-test", value=False)
if run_checks:
    try:
        models = oai.models.list()
        st.success(f"OpenAI OK · {len(models.data)} models visible.")
    except Exception as e:
        st.error(f"OpenAI error: {e}")
    if POLYGON_API_KEY:
        try:
            prev = polygon_get("/v2/aggs/ticker/AAPL/prev", {"adjusted": "true"})
            st.success("Polygon OK · sample keys: " + ", ".join(list(prev.keys())[:5]))
        except Exception as e:
            st.error(f"Polygon error: {e}")
    else:
        st.warning("Polygon key not set.")

# --- END HEADER v2 ---
