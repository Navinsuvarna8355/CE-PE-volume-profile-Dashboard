import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import random
import requests

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
# Inputs
# -------------------------------
col_exp1, col_exp2 = st.columns(2)
with col_exp1:
    expiry_bn = st.date_input("📅 Bank Nifty Expiry", value=datetime(2025, 9, 18))
with col_exp2:
    expiry_nf = st.date_input("📅 Nifty Expiry", value=datetime(2025, 9, 19))

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
        ce_theta = round(random.uniform(20, 70), 2)
        pe_theta = 0
        ce_change = 0
        pe_change = 0
        decay_bias = "PE" if ce_theta > pe_theta else "CE"
        data.append({
            "Strike Price": strike,
            "PE Theta": pe_theta,
            "CE Theta": ce_theta,
            "CE Change": ce_change,
            "PE Change": pe_change,
            "Decay Bias": decay_bias
        })
    return pd.DataFrame(data)

df_bn = generate_theta_table(spot_bn)
df_nf = generate_theta_table(spot_nf)

# -------------------------------
# Bias Detection
# -------------------------------
def detect_bias(df):
    bias_counts = df["Decay Bias"].value_counts()
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
    st.markdown(strategy_bn)

with tab2:
    st.markdown(f"### 📍 Spot Price: `{spot_nf}`")
    st.markdown(f"### 📅 Expiry Date: `{expiry_nf.strftime('%d-%b-%Y')}`")
    st.markdown(f"### 📊 Decay Bias: `{bias_nf}`")
    st.subheader("📊 Analysis")
    st.dataframe(df_nf, use_container_width=True)
    st.subheader("🎯 Trading Recommendations")
    st.markdown(strategy_nf)
