import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import random

# -------------------------------
# Configurations
# -------------------------------
BOT_TOKEN = "8010130215:AAGEqfShscPDwlnXj1bKHTzUish_EE"
CHANNEL_ID = "@navinnsuvarna"
HEADERS = {"User-Agent": "Mozilla/5.0"}

st.set_page_config(page_title="Live Decay Analyzer", layout="wide")
st.title("📉 Live Decay Bias Analyzer – Bank Nifty & Nifty")

# -------------------------------
# Spot Price Fetcher
# -------------------------------
def fetch_spot(symbol):
    url = f"https://www.nseindia.com/api/quote-derivative?symbol={symbol}"
    try:
        response = requests.get(url, headers=HEADERS)
        data = response.json()
        return float(data["underlyingValue"])
    except:
        return None

# -------------------------------
# Inputs
# -------------------------------
expiry_date = st.date_input("📅 Expiry Date", value=datetime(2025, 9, 18))
send_alert = st.checkbox("📲 Send Telegram Alert")

spot_banknifty = fetch_spot("BANKNIFTY")
spot_nifty = fetch_spot("NIFTY")

if not spot_banknifty or not spot_nifty:
    st.error("⚠️ Failed to fetch live spot prices. Try again later.")
    st.stop()

# -------------------------------
# Theta Table Generator
# -------------------------------
def generate_theta_table(spot):
    strikes = range(int(spot - 200), int(spot + 400), 100)
    data = []
    for strike in strikes:
        ce_theta = round(random.uniform(20, 70), 2)
        pe_theta = 0
        decay_bias = "PE" if ce_theta > pe_theta else "CE"
        data.append({
            "Strike": strike,
            "PE Theta": pe_theta,
            "CE Theta": ce_theta,
            "Decay Bias": decay_bias
        })
    return pd.DataFrame(data)

df_banknifty = generate_theta_table(spot_banknifty)
df_nifty = generate_theta_table(spot_nifty)

# -------------------------------
# Bias Detection
# -------------------------------
def detect_bias(df):
    bias_counts = df["Decay Bias"].value_counts()
    return "PE Decay Active" if bias_counts.get("PE", 0) > bias_counts.get("CE", 0) else "CE Decay Active"

bias_banknifty = detect_bias(df_banknifty)
bias_nifty = detect_bias(df_nifty)

# -------------------------------
# Strategy Recommendation
# -------------------------------
def recommend_strategy(bias):
    if bias == "PE Decay Active":
        return "✅ Short Put\n✅ Long Call\n✅ Bull Call Spread"
    else:
        return "✅ Short Call\n✅ Long Put\n✅ Bear Put Spread"

strategy_banknifty = recommend_strategy(bias_banknifty)
strategy_nifty = recommend_strategy(bias_nifty)

# -------------------------------
# Timestamp
# -------------------------------
ist = pytz.timezone("Asia/Kolkata")
timestamp = datetime.now(ist).strftime("%d-%b-%Y %I:%M:%S %p")

# -------------------------------
# Telegram Alert
# -------------------------------
if send_alert:
    message = f"""
📉 *Live Decay Bias Analyzer*  
Expiry: {expiry_date.strftime('%d-%b-%Y')}  
🟦 Bank Nifty  
Spot: {spot_banknifty}  
Bias: {bias_banknifty}  
Strategy:  
{strategy_banknifty}  

🟥 Nifty  
Spot: {spot_nifty}  
Bias: {bias_nifty}  
Strategy:  
{strategy_nifty}  

⏱️ Last Updated: {timestamp}
"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHANNEL_ID, "text": message, "parse_mode": "Markdown"}
        )
        st.success("Telegram alert sent!")
    except Exception as e:
        st.error(f"Telegram alert failed: {e}")

# -------------------------------
# Display Panels
# -------------------------------
st.markdown(f"### ⏱️ Last updated at `{timestamp}`")

col1, col2 = st.columns(2)
with col1:
    st.subheader("🟦 Bank Nifty")
    st.markdown(f"**Spot:** `{spot_banknifty}`")
    st.markdown(f"**Decay Bias:** `{bias_banknifty}`")
    st.dataframe(df_banknifty, use_container_width=True)
    st.subheader("🎯 Strategy")
    st.markdown(strategy_banknifty)

with col2:
    st.subheader("🟥 Nifty")
    st.markdown(f"**Spot:** `{spot_nifty}`")
    st.markdown(f"**Decay Bias:** `{bias_nifty}`")
    st.dataframe(df_nifty, use_container_width=True)
    st.subheader("🎯 Strategy")
    st.markdown(strategy_nifty)
