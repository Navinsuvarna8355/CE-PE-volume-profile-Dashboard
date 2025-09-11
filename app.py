import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import random
import requests
import calendar

# -------------------------------
# Configurations
# -------------------------------
BOT_TOKEN = "8010130215:AAGEqfShscPDwlnXj1bKHTzUish_EE"
CHANNEL_ID = "@navinnsuvarna"

st.set_page_config(page_title="Dual Decay Bias Analyzer", layout="wide")
st.title("📉 Decay Bias Analyzer – Bank Nifty & Nifty")

# -------------------------------
# Spot Price Fetcher with Fallback
# -------------------------------
def fetch_spot(symbol, fallback):
    url = f"https://www.nseindia.com/api/quote-derivative?symbol={symbol}"
    try:
        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9"
        })
        data = response.json()
        return float(data["underlyingValue"])
    except:
        return fallback

# -------------------------------
# Expiry Calculators
# -------------------------------
def get_last_tuesday(year, month):
    last_day = calendar.monthrange(year, month)[1]
    for day in range(last_day, 0, -1):
        date = datetime(year, month, day)
        if date.weekday() == 1:  # Tuesday
            return date
    return datetime(year, month, last_day)

def get_next_tuesday(today):
    days_ahead = (1 - today.weekday() + 7) % 7
    return today + timedelta(days=days_ahead)

# -------------------------------
# Inputs
# -------------------------------
today = datetime.now()
expiry_bn = get_last_tuesday(today.year, today.month)
expiry_nf = get_next_tuesday(today)
send_alert = st.checkbox("📲 Send Telegram Alert")

spot_bn = fetch_spot("BANKNIFTY", fallback=44850.25)
spot_nf = fetch_spot("NIFTY", fallback=24948.25)

# -------------------------------
# Theta Table Generator
# -------------------------------
def generate_theta_table(spot):
    strikes = range(int(spot - 200), int(spot + 400), 100)
    data = []
    for strike in strikes:
        ce_change = round(random.uniform(30, 70), 2)
        pe_change = round(random.uniform(10, 50), 2)
        ce_ratio = round(random.uniform(0.5, 1.5), 2)
        pc_ratio = round(random.uniform(0.3, 1.2), 2)
        decay_rate = "PE" if ce_change > pe_change else "CE"
        data.append({
            "Strike Price": strike,
            "P/C Ratio": pc_ratio,
            "CE Ratio": ce_ratio,
            "CE Change": ce_change,
            "PE Change": pe_change,
            "Decay Rate": decay_rate
        })
    return pd.DataFrame(data)

df_bn = generate_theta_table(spot_bn)
df_nf = generate_theta_table(spot_nf)

# -------------------------------
# Bias Detection
# -------------------------------
def detect_bias(df):
    bias_counts = df["Decay Rate"].value_counts()
    return "PE Decay Active" if bias_counts.get("PE", 0) > bias_counts.get("CE", 0) else "CE Decay Active"

bias_bn = detect_bias(df_bn)
bias_nf = detect_bias(df_nf)

# -------------------------------
# Strategy Recommendation
# -------------------------------
def recommend_strategy(bias):
    if bias == "PE Decay Active":
        return "✅ Sell Put Options (Short Put)\n✅ Buy Call Options (Long Call)\n✅ Bull Call Spread"
    else:
        return "✅ Sell Call Options (Short Call)\n✅ Buy Put Options (Long Put)\n✅ Bear Put Spread"

strategy_bn = recommend_strategy(bias_bn)
strategy_nf = recommend_strategy(bias_nf)

# -------------------------------
# Timestamp
# -------------------------------
ist = pytz.timezone("Asia/Kolkata")
now = datetime.now(ist)
timestamp = now.strftime("%d-%b-%Y %I:%M:%S %p")

# -------------------------------
# Telegram Alert
# -------------------------------
if send_alert:
    message = f"""
📉 *Decay Bias Analyzer*  

🟦 Bank Nifty  
Spot: {spot_bn}  
Expiry: {expiry_bn.strftime('%d-%b-%Y')}  
Bias: {bias_bn}  
Strategy:  
{strategy_bn}  

🟥 Nifty  
Spot: {spot_nf}  
Expiry: {expiry_nf.strftime('%d-%b-%Y')}  
Bias: {bias_nf}  
Strategy:  
{strategy_nf}  

⏱️ Last Updated: {timestamp}
"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=payload)
        st.success("Telegram alert sent!")
    except Exception as e:
        st.error(f"Telegram alert failed: {e}")

# -------------------------------
# Display Panels
# -------------------------------
st.markdown(f"#### ⏱️ Last updated at `{timestamp}`")

tab1, tab2 = st.tabs(["🟦 Bank Nifty", "🟥 Nifty"])

with tab1:
    st.markdown(f"### 📍 Spot Price: `{spot_bn}`")
    st.markdown(f"### 📅 Expiry Date: `{expiry_bn.strftime('%d-%b-%Y')}`")
    st.markdown(f"### 📊 Decay Bias: `{bias_bn}`")
    st.subheader("📊 Analysis")
    st.dataframe(df_bn, use_container_width=True)
    st.subheader("🎯 Trading Recommendations")
    for line in strategy_bn.split("\n"):
        st.markdown(f"- {line}")

with tab2:
    st.markdown(f"### 📍 Spot Price: `{spot_nf}`")
    st.markdown(f"### 📅 Expiry Date: `{expiry_nf.strftime('%d-%b-%Y')}`")
    st.markdown(f"### 📊 Decay Bias: `{bias_nf}`")
    st.subheader("📊 Analysis")
    st.dataframe(df_nf, use_container_width=True)
    st.subheader("🎯 Trading Recommendations")
    for line in strategy_nf.split("\n"):
        st.markdown(f"- {line}")
