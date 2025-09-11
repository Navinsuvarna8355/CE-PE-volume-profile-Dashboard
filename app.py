# streamlit_dashboard_options_decay.py

# -----------------------------------------
# [1] Imports and Global Configuration Block
# -----------------------------------------
import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy.stats import norm

# Optional for Telegram
# from telegram import Bot

# For performance: set Streamlit config, cache where practical
st.set_page_config(page_title="Bank Nifty / Nifty Options Decay Bias", layout="wide")
CACHE_TTL = 45  # seconds

# -----------------------------------------
# [2] Helper Functions: API, Greeks, Error Handling
# -----------------------------------------

# -- API session builder
def create_nse_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br'
    })
    try:
        session.get('https://www.nseindia.com', timeout=5)
    except Exception:
        st.warning("Warning: Cannot pre-fetch cookies from NSEIndia. Attempting anyway.")
    return session


# -- Option Chain Fetcher [with error handling]
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def fetch_option_chain(symbol):
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    session = create_nse_session()
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data
    except Exception as ex:
        st.error(f"[{symbol}] Failed to fetch option chain: {ex}")
        return None

# -- Spot Price Fetcher
def fetch_spot_price(chain_json):
    if not chain_json or "records" not in chain_json:
        return None
    return float(chain_json['records'].get("underlyingValue", np.nan))

# -- Expiry Dates Extractor
def extract_expiry_dates(chain_json):
    if not chain_json or "records" not in chain_json:
        return []
    return chain_json["records"].get('expiryDates', [])

# -- Option Table Parser
def parse_option_table(chain_json, expiry):
    records = chain_json["records"]["data"]
    strikes = []
    ce_data, pe_data = [], []
    for rec in records:
        if rec.get("expiryDate") != expiry:
            continue
        strikes.append(rec["strikePrice"])
        ce = rec.get("CE", {})
        pe = rec.get("PE", {})
        ce_data.append({
            "LTP": ce.get("lastPrice"), "IV": ce.get("impliedVolatility"), "Theta": ce.get('theta'), "OI": ce.get("openInterest")
        })
        pe_data.append({
            "LTP": pe.get("lastPrice"), "IV": pe.get("impliedVolatility"), "Theta": pe.get('theta'), "OI": pe.get("openInterest")
        })
    return strikes, ce_data, pe_data

# -- (If theta not available in source, see Black-Scholes method above)

# -- Decay Bias Detection
def detect_decay_bias(ce_df, pe_df, atm_idx=0):
    # Use the nearest-to-ATM ±2 strikes for average. Assume sorted.
    n_atm = 2
    ce_thetas = np.array([v for v in ce_df['Theta'][atm_idx-n_atm:atm_idx+n_atm+1] if v is not None])
    pe_thetas = np.array([v for v in pe_df['Theta'][atm_idx-n_atm:atm_idx+n_atm+1] if v is not None])
    mean_ce_theta = np.nanmean(np.abs(ce_thetas))
    mean_pe_theta = np.nanmean(np.abs(pe_thetas))
    if mean_ce_theta > 1.1 * mean_pe_theta:
        return "calls", mean_ce_theta, mean_pe_theta
    elif mean_pe_theta > 1.1 * mean_ce_theta:
        return "puts", mean_ce_theta, mean_pe_theta
    else:
        return "neutral", mean_ce_theta, mean_pe_theta

# -- Strategy Recommendation
def recommend_strategy(bias, spot, atm_strike, expiry, iv_level, is_weekly):
    if bias == "calls":
        return (f"Detected stronger decay on the CALL side (θ ↑). "
                f"Suggested: Short/credit spreads or naked calls ATM/OTM ({atm_strike}, expiry {expiry}). "
                f"Iron condor with call leg further OTM if IV is moderate ({iv_level:.1f}%).")
    elif bias == "puts":
        return (f"Detected stronger decay on the PUT side (θ ↑). "
                f"Suggested: Short puts or bull put spreads ATM/OTM ({atm_strike}, expiry {expiry}). "
                f"Iron condor with put leg further OTM if IV moderate ({iv_level:.1f}%).")
    else:
        return ("Decay appears balanced. Consider strangles, iron condors, or ATM credit spreads. "
                f"Monitor IV ({iv_level:.1f}%), consider entry only if IV > recent average.")

# -- Telegram Alert Sender (optional, pseudocode)
def send_telegram_alert(token, chat_id, message):
    # bot = Bot(token=token)
    # bot.send_message(chat_id=chat_id, text=message)
    pass  # Integration optional

# -----------------------------------------
# [3] Streamlit App Starts Here
# -----------------------------------------
st.title("Live Bank Nifty & Nifty Options Decay Bias Dashboard")

# --- Sidebar for Navigation ---
selected_index = st.sidebar.selectbox("Index", ["NIFTY", "BANKNIFTY"])
alert_on = st.sidebar.checkbox("Enable Telegram Alerts (optional)")
telegram_token = st.sidebar.text_input("Telegram Bot Token", type="password")
telegram_chat_id = st.sidebar.text_input("Telegram Chat ID")
refresh_interval = st.sidebar.number_input("Refresh interval (sec)", value=30, step=5, min_value=15, max_value=120)

# --- Autorefresh
from streamlit_autorefresh import st_autorefresh
count = st_autorefresh(interval=refresh_interval*1000, key="datareload")

st.header(f"Live Data Fetch: {selected_index}")

# -- Fetch Option Chain Data (Main)
with st.spinner("Fetching latest data..."):
    chain_json = fetch_option_chain(selected_index)
    spot = fetch_spot_price(chain_json)
    expiry_dates = extract_expiry_dates(chain_json)

if not chain_json:
    st.stop()
if spot is not None:
    st.metric(f"{selected_index} Spot Price", f"{spot:,.2f}")

# -- Expiry Date Selection
expiry = st.selectbox("Select Option Chain Expiry", expiry_dates)
strikes, ce_data, pe_data = parse_option_table(chain_json, expiry)

# -- Build DataFrame for Table Display
df = pd.DataFrame({
    "Strike": strikes,
    "Call LTP": [row["LTP"] for row in ce_data],
    "Call IV": [row["IV"] for row in ce_data],
    "Call Theta": [row["Theta"] for row in ce_data],
    "Put LTP": [row["LTP"] for row in pe_data],
    "Put IV": [row["IV"] for row in pe_data],
    "Put Theta": [row["Theta"] for row in pe_data],
})
atm_idx = (np.abs(df["Strike"] - spot)).idxmin()

# -- CE/PE Theta Table Section
st.subheader("Option Chain CE/PE Theta Table")
st.dataframe(df.style.highlight_max(axis=0, subset=["Call Theta", "Put Theta"], color="lightcoral"))

# -- Decay Bias Detection Section
st.subheader("Decay Bias Detection")
bias, ce_theta, pe_theta = detect_decay_bias(df[['Call Theta']], df[['Put Theta']], atm_idx)
bias_desc = f"Decay Bias: **{bias.upper()}** (Mean CE θ: {ce_theta:.2f}, Mean PE θ: {pe_theta:.2f})"
st.markdown(bias_desc)

# -- Strategy Recommendation Section
st.subheader("Strategy Recommendation Engine")
atm_strike = df.iloc[atm_idx]["Strike"]
iv_level = (df.iloc[atm_idx]["Call IV"] + df.iloc[atm_idx]["Put IV"])/2
strategy = recommend_strategy(bias, spot, atm_strike, expiry, iv_level, is_weekly="WEEKLY" in expiry)
st.info(strategy)

# -- Timestamp Display & Meta
now = datetime.now()
st.caption(f"Data as of: {now.strftime('%Y-%m-%d %H:%M:%S')} | Auto-refresh every {refresh_interval} seconds.")

# -- Optional: Telegram Alerts
if alert_on and telegram_token and telegram_chat_id:
    alert_msg = (f"[{now.strftime('%H:%M:%S')}] {selected_index} | {bias_desc}\n{strategy}")
    # send_telegram_alert(telegram_token, telegram_chat_id, alert_msg)
    st.success("Telegram Alert (Sample):\n" + alert_msg)

# -- (Extra) Visualization: Theta Heatmaps, OI plots, IV chart, etc. could be easily added

# -----------------------------------------
# [END SCRIPT]
# -----------------------------------------
