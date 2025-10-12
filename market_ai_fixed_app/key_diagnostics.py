
# save as key_diagnostics.py and run with: streamlit run key_diagnostics.py
import os, re
import streamlit as st

def mask(key: str) -> str:
    if not key:
        return "NONE"
    return key[:6] + "…" + key[-6:]

st.title("🔐 OpenAI/Polygon Key Diagnostics")

# Prefer Streamlit secrets, but also show env fallbacks so you can see conflicts
st.subheader("Sources")
s_secret = None
try:
    s_secret = st.secrets.get("OPENAI_API_KEY", None)
except Exception:
    s_secret = None
st.write("st.secrets['OPENAI_API_KEY']:", mask(s_secret) if s_secret else "NONE")

e_secret = os.getenv("OPENAI_API_KEY")
st.write("env OPENAI_API_KEY:", mask(e_secret) if e_secret else "NONE")

st.divider()
key = s_secret or e_secret
if not key:
    st.error("No OpenAI key found in st.secrets or environment.")
    st.stop()

# Checks
st.subheader("Checks")
is_project = key.startswith("sk-proj-")
is_personal = key.startswith("sk-") and not is_project
st.write("Starts with 'sk-proj-' →", is_project)
st.write("Starts with 'sk-' (personal) →", is_personal)
st.write("Length →", len(key))
st.write("Contains whitespace →", bool(re.search(r"\s", key)))
st.write("Contains quotes →", ('"' in key) or ('\'' in key))

if is_project:
    st.error("You are using a PROJECT key (sk-proj-). Replace with a PERSONAL key (sk-...).")
elif not is_personal:
    st.warning("Key does not look like a standard personal key (sk-...). Double-check you pasted it correctly.")
else:
    st.success("Key format looks like a personal key.")

st.info("If both st.secrets and env are set, your app code may be reading the ENV first. Ensure your code uses st.secrets or remove the env var.")
