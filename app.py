# ===============================================================
#  Nifty Options Decay Bias Streamlit Dashboard
# ===============================================================

import streamlit as st
import pandas as pd
import requests
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import asyncio

# -- Constants and Settings --------------------------------------
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
TELEGRAM_USER_ID = st.secrets.get("TELEGRAM_USER_ID", "")

st.set_page_config(page_title="Nifty Options Decay Bias", layout="wide")

# ===============================================================
#  Helper Functions
# ===============================================================

def get_live_nifty_price():
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        return res.json()['records']['underlyingValue']
    except Exception:
        return None

@st.cache_data(ttl=60)
def fetch_option_chain_data():
    # Returns the entire option chain JSON, refreshed every 1 min
    headers = {'User-Agent': 'Mozilla/5.0'}
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    res = requests.get(url, headers=headers, timeout=10)
    res.raise_for_status()
    return res.json()['records']['data']

def get_expiry_dates(option_chain_data):
    return sorted(set(item['expiryDate'] for item in option_chain_data))

def build_theta_table(option_chain, expiry):
    rows = []
    for item in option_chain:
        if item['expiryDate'] == expiry:
            strike = item['strikePrice']
            ce = item.get('CE', {})
            pe = item.get('PE', {})
            ce_theta = ce.get('theta', np.nan)
            pe_theta = pe.get('theta', np.nan)
            rows.append({
                'Strike': strike,
                'CE Theta': ce_theta,
                'PE Theta': pe_theta,
                'Decay Bias': (ce_theta - pe_theta) if np.isfinite(ce_theta) and np.isfinite(pe_theta) else np.nan,
            })
    df = pd.DataFrame(rows).sort_values('Strike')
    df['Bias Direction'] = np.where(df['Decay Bias'] > 0, 'CE', 'PE')
    return df

def generate_ce_theta_chart(df):
    fig, ax = plt.subplots(figsize=(10,5))
    plotted = ax.plot(df['Strike'], df['CE Theta'], marker='o', color='blue', label='CE Theta')
    ax.set_xlabel("Strike Price")
    ax.set_ylabel("Theta")
    ax.set_title("CE Theta Decay Across Strikes")
    ax.grid(True)
    ax.legend()
    return fig

def recommend_strategy(df):
    ce_bias = (df['Bias Direction'] == 'CE').sum()
    pe_bias = (df['Bias Direction'] == 'PE').sum()
    if ce_bias > pe_bias:
        return "PE Short Strategy favored (CE decay is higher)"
    elif pe_bias > ce_bias:
        return "CE Short Strategy favored (PE decay is higher)"
    else:
        return "Neutral Bias – Consider Iron Condor/Straddle"

async def send_telegram_alert(message):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_USER_ID:
        import aiohttp
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_USER_ID, "text": message}
        async with aiohttp.ClientSession() as session:
            await session.post(url, data=payload)

# ===============================================================
#  Streamlit Layout and Dashboard Structure
# ===============================================================

st.title("🔍 Nifty Options Decay Bias Dashboard")

# Sidebar: Live Metrics and Controls
with st.sidebar:
    spot_price = get_live_nifty_price()
    st.metric("Live Nifty Spot", f"{spot_price:.2f}" if spot_price else "N/A")
    last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    st.markdown(f"**Last Updated:** {last_update}")
    telegram_enabled = st.checkbox("Enable Telegram Alerts")
    auto_refresh = st.checkbox("Auto-refresh (60s)", value=True)
    # can add st_autorefresh(interval=60000) here per Section 9.2

# Main: Expiry Selector and Data Loading
option_chain_data = fetch_option_chain_data()
expiry_options = get_expiry_dates(option_chain_data)
selected_expiry = st.selectbox("Select Expiry Date", expiry_options)

theta_df = build_theta_table(option_chain_data, selected_expiry)

# Strategy Recommendation Engine
average_bias = theta_df['Decay Bias'].mean()
strategy = recommend_strategy(theta_df)
st.success(f"🧭 Strategy Recommendation: {strategy}")

if telegram_enabled:
    asyncio.run(send_telegram_alert(f"Nifty Decay Bias: Strategy - {strategy} @ {last_update}"))

# Tabs Layout: DataTable and Chart
tab1, tab2 = st.tabs(["📊 CE/PE Theta Table", "📈 CE Theta Chart"])
with tab1:
    st.dataframe(
        theta_df.style.background_gradient(subset=["Decay Bias"], cmap="coolwarm"), 
        use_container_width=True
    )
with tab2:
    fig = generate_ce_theta_chart(theta_df)
    st.pyplot(fig)

st.caption("NB: All calculations use latest available NSE data; theoretical Greeks may show as NaN for illiquid strikes.")

# Optional: Further extension for advanced filters, historical decay curves, or backtesting engine

# ===============================================================
# END OF FILE
# ===============================================================
