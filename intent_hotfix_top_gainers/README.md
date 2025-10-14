
# Intent Hotfix: "Predict highest riser today"

This patch adds:
- Fetch **today's top gainers** (Polygon snapshot -> Alpha Vantage fallback)
- **Model ranking** using your existing predictor (`modules/predictor.py`)
- A simple **intent handler** you can call from chat

## 1) Add to your repo
Create a folder `intent_hotfix_top_gainers/` next to `app.py` and place `tools_additions.py` inside.

Layout example:
```
app.py
tools.py
modules/
intent_hotfix_top_gainers/
  └─ tools_additions.py
```

## 2) Wire into chat
In `app.py` (or wherever you process chat), add:
```python
from intent_hotfix_top_gainers.tools_additions import handle_top_gainer_query
from modules.predictor import predict_direction
from tools import _download_yf
import re

# inside your chat handler when user_text arrives:
text = (user_text or "").strip()
if re.search(r"(highest\s+riser|top\s+gainer|biggest\s+mover)", text, re.I):
    answer = handle_top_gainer_query(_download_yf, predict_direction, limit=10, horizon_days=7)
    st.session_state.history.append(("assistant", answer))
    st.chat_message("assistant").markdown(answer)
    st.stop()
```

## 3) Secrets required
In Streamlit → Settings → Secrets, ensure you have at least one:
```
POLYGON_API_KEY = "your-polygon-key"
ALPHAVANTAGE_API_KEY = "your-av-key"
```

## 4) Test
Ask your app: **predict highest riser today** or **top gainer today**.
You should see a model pick plus a short ranked list.
