import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime
import pytz
import random

# -------------------------------
# Configurations
# -------------------------------
BOT_TOKEN = "8010130215:AAGEqfShscPDwlnXj1bKHTzUish_EE"
CHANNEL_ID = "@navinnsuvarna"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}

st.set_page_config(page_title="Dual Decay Analyzer", layout="wide")
st.title("📉 Decay Bias Analyzer – Bank Nifty & Nifty")

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

spot_bn = fetch_spot("BANKNIFTY")
spot_nf = fetch_spot("NIFTY")

if not spot_bn or not spot_nf:
    st.error("⚠️ Failed to fetch live spot prices. Try again later.")
    st.stop()

# -------------------------------
# Theta Table Generator
# -------------------------------
def generate_theta_table(spot):
    strikes = range(int(spot - 200), int(spot + 500), 100)
    data = []
    ce_thetas = []
    for strike in strikes:
        ce_theta = round(random.uniform(1.5, 3.5), 2)
        pe_theta = 0
        decay_side = "CE" if ce_theta > pe_theta else "PE"
        data.append({
            "Strike Price": strike,
            "CE Theta": ce_theta,
            "PE Theta": pe_theta,
            "CE Change": 0,
            "PE Change": 0,
            "Decay Side": decay_side
        })
        ce_thetas.append((strike, ce_theta))
    return pd.DataFrame(data), ce_thetas

df_bn, chart_bn = generate_theta_table(spot_bn)
df_nf, chart_nf = generate_theta_table(spot_nf)

# -------------------------------
# Bias Detection
# -------------------------------
def detect_bias(df):
    bias_counts = df["Decay Side"].value_counts()
    return "CE Decay Active" if bias_counts.get("CE", 0) > bias_counts.get("PE", 0) else "PE Decay Active"

bias_bn = detect_bias(df_bn)
bias_nf = detect_bias(df_nf)

# -------------------------------
# Strategy Recommendation
# -------------------------------
def recommend_strategy(bias):
    if bias == "CE Decay Active":
        return "📉 Bearish Bias:\n✅ Short Call\n✅ Long Put\n✅ Bear Put Spread"
    else:
        return "📈 Bullish Bias:\n✅ Short Put\n✅ Long Call\n✅ Bull Call Spread"

strategy_bn = recommend_strategy(bias_bn)
strategy_nf = recommend_strategy(bias_nf)

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
📉 *Decay Bias Analyzer*  
Expiry: {expiry_date.strftime('%d-%b-%Y')}  
🟦 Bank Nifty  
Spot: {spot_bn}  
Bias: {bias_bn}  
Strategy:  
{strategy_bn}  

🟥 Nifty  
Spot: {spot_nf}  
Bias: {bias_nf}  
Strategy:  
{strategy_nf}  

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
# Chart Plotter
# -------------------------------
def plot_theta_chart(data, title):
    strikes, ce_values = zip(*data)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=strikes, y=ce_values, mode='lines+markers', name='CE Theta', line=dict(color='blue')))
    fig.update_layout(title=title, xaxis_title="Strike Price", yaxis_title="CE Theta", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# Display Panels
# -------------------------------
st.markdown(f"### ⏱️ Last updated at `{timestamp}`")

tab_bn, tab_nf = st.tabs(["🟦 Bank Nifty", "🟥 Nifty"])

with tab_bn:
    st.markdown(f"**Spot:** `{spot_bn}`")
    st.markdown(f"**Decay Bias:** `{bias_bn}`")
    st.subheader("📊 Data Table")
    st.dataframe(df_bn, use_container_width=True)
    st.subheader("📈 Theta Chart")
    plot_theta_chart(chart_bn, "Bank Nifty CE Theta Decay")
    st.subheader("🎯 Strategy Recommendation")
    st.markdown(strategy_bn)

with tab_nf:
    st.markdown(f"**Spot:** `{spot_nf}`")
    st.markdown(f"**Decay Bias:** `{bias_nf}`")
    st.subheader("📊 Data Table")
    st.dataframe(df_nf, use_container_width=True)
    st.subheader("📈 Theta Chart")
    plot_theta_chart(chart_nf, "Nifty CE Theta Decay")
    st.subheader("🎯 Strategy Recommendation")
    st.markdown(strategy_nf)
