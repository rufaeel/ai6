
# Highest Riser Today — Full Intent Patch

This adds exactly what you asked for:
- **Fetch today’s top gainers** (Polygon `/v2/snapshot/locale/us/markets/stocks/gainers`).
- **Fallback**: Alpha Vantage TOP_GAINERS_LOSERS if Polygon isn’t available.
- **Run your predictor** (`predict_direction(...)` or your aggressive variant) on each candidate.
- **Compute** `expected_return_pct` and `prob_up`.
- **Rank** by expected return (then probability).
- **Format** the reply for chat as:
  ```
  Model pick: XYZ
  Prob(up): 0.67
  Expected return: 4.2%
  Today’s gain: +3.5%
  ```

## Install
1) Put the folder next to your `app.py`:
```
app.py
intent_hotfix_top_gainers/
  └─ tools_additions.py
modules/
```
2) Wire into your chat handler (in `app.py` or `llm.py`):
```python
from intent_hotfix_top_gainers.tools_additions import handle_highest_riser_intent
from modules.predictor import predict_direction
from tools import _download_yf
import re

text = (user_text or "").strip()
if re.search(r"(highest\s+riser|top\s+gainer|rise\s+highest\s+today|which\s+stock\s+will\s+rise\s+most\s+today)", text, re.I):
    answer = handle_highest_riser_intent(_download_yf, predict_direction, limit=10, horizon_days=7)
    st.session_state.history.append(("assistant", answer))
    st.chat_message("assistant").markdown(answer)
    st.stop()
```
3) Secrets required (Streamlit → Settings → Secrets):
```toml
POLYGON_API_KEY = "your-polygon-key"           # preferred
ALPHAVANTAGE_API_KEY = "your-alphavantage-key" # fallback
```
4) Dependencies (root `requirements.txt`):
```
streamlit
pandas
requests
yfinance
python-dotenv
openai
vaderSentiment
```
5) Redeploy the app and test:
- Ask: **which stock will rise most today**
- Or: **predict highest riser today**
