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

st.set_page_config(page_title="Decay Bias Analyzer", layout="wide")
st.title("📉 Decay Bias Analyzer – Tactical Dashboard")

# -------------------------------
# Inputs
# -------------------------------
spot_price = st.number_input("📍 My Spot Price", value=24948.25)
expiry_date = st.date_input("📅 Expiry Date", value=datetime(2025, 9, 15))
send_alert = st.checkbox("📲 Send Telegram Alert")

# -------------------------------
# Generate Theta Table
# -------------------------------
strike_range = range(int(spot_price - 200), int(spot_price + 400), 100)
data = []
for strike in strike_range:
    ce_theta = round(random.uniform(20, 70), 2)
    pe_theta = 0  # Assume PE theta is decaying slower
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

df = pd.DataFrame(data)

# -------------------------------
# Bias Detection
# -------------------------------
bias_counts = df["Decay Bias"].value_counts()
dominant_bias = "PE Decay Active" if bias_counts.get("PE", 0) > bias_counts.get("CE", 0) else "CE Decay Active"

# -------------------------------
# Strategy Recommendation
# -------------------------------
strategy = ""
if dominant_bias == "PE Decay Active":
    strategy = "✅ Sell Put Options (Short Put)\n✅ Buy Call Options (Long Call)\n✅ Bull Call Spread"
else:
    strategy = "✅ Sell Call Options (Short Call)\n✅ Buy Put Options (Long Put)\n✅ Bear Put Spread"

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
Spot Price: {spot_price}  
Expiry: {expiry_date.strftime('%d-%b-%Y')}  
Bias: {dominant_bias}  
Recommended Strategies:  
{strategy}  
Last Updated: {timestamp}
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
st.markdown(f"### 📍 My Spot Price: `{spot_price}`")
st.markdown(f"### 📅 Expiry Date: `{expiry_date.strftime('%d-%b-%Y')}`")
st.markdown(f"### 📊 Decay Bias: `{dominant_bias}`")
st.markdown(f"#### ⏱️ Last updated at `{timestamp}`")

st.subheader("📊 Analysis")
st.dataframe(df, use_container_width=True)

st.subheader("🎯 Trading Recommendations")
st.markdown(strategy)
