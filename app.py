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
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}

st.set_page_config(page_title="Decay Bias Analyzer", layout="wide")
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
expiry_date = st.date_input("📅 Expiry Date", value=datetime(2025, 9, 15))
send_alert = st.checkbox("📲 Send Telegram Alert")
price_direction = st.selectbox("📈 Price Direction", ["Up", "Down", "Sideways"])

spot_bn = fetch_spot("BANKNIFTY")
spot_nf = fetch_spot("NIFTY")

if not spot_bn or not spot_nf:
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
            "Strike Price": strike,
            "PE Theta": pe_theta,
            "CE Theta": ce_theta,
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
# Trap Trade Detection
# -------------------------------
def detect_trap(bias, direction):
    if (bias == "CE Decay Active" and direction == "Up") or \
       (bias == "PE Decay Active" and direction == "Down"):
        return "⚠️ Potential Trap Trade"
    return "✅ Bias aligned with price"

trap_bn = detect_trap(bias_bn, price_direction)
trap_nf = detect_trap(bias_nf, price_direction)

# -------------------------------
# Strategy Recommendation
# -------------------------------
def recommend_strategy(bias):
    if bias == "PE Decay Active":
        return "✅ Short Put\n✅ Long Call\n✅ Bull Call Spread"
    else:
        return "✅ Short Call\n✅ Long Put\n✅ Bear Put Spread"

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
Direction: {price_direction}  

🟦 Bank Nifty  
Spot: {spot_bn}  
Bias: {bias_bn}  
Trap: {trap_bn}  
Strategy:  
{strategy_bn}  

🟥 Nifty  
Spot: {spot_nf}  
Bias: {bias_nf}  
Trap: {trap_nf}  
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
# Backtest Module (Synthetic)
# -------------------------------
def run_backtest():
    results = []
    for day in range(1, 11):
        ce_theta = random.uniform(20, 70)
        pe_theta = 0
        bias = "PE" if ce_theta > pe_theta else "CE"
        direction = random.choice(["Up", "Down"])
        trap = detect_trap("PE Decay Active" if bias == "PE" else "CE Decay Active", direction)
        pnl = random.uniform(-1500, 2500) if "✅" in trap else random.uniform(-3000, 1000)
        results.append({
            "Day": f"Day {day}",
            "Bias": bias,
            "Direction": direction,
            "Trap": trap,
            "PnL": round(pnl, 2)
        })
    return pd.DataFrame(results)

# -------------------------------
# Display Panels
# -------------------------------
st.markdown(f"### ⏱️ Last updated at `{timestamp}`")

tab1, tab2, tab3 = st.tabs(["🟦 Bank Nifty", "🟥 Nifty", "📊 Backtest"])

with tab1:
    st.markdown(f"**Spot:** `{spot_bn}`")
    st.markdown(f"**Decay Bias:** `{bias_bn}`")
    st.markdown(f"**Trap Filter:** `{trap_bn}`")
    st.dataframe(df_bn, use_container_width=True)
    st.subheader("🎯 Strategy")
    st.markdown(strategy_bn)

with tab2:
    st.markdown(f"**Spot:** `{spot_nf}`")
    st.markdown(f"**Decay Bias:** `{bias_nf}`")
    st.markdown(f"**Trap Filter:** `{trap_nf}`")
    st.dataframe(df_nf, use_container_width=True)
    st.subheader("🎯 Strategy")
    st.markdown(strategy_nf)

with tab3:
    st.subheader("📊 Backtest Results (Synthetic)")
    df_bt = run_backtest()
    st.dataframe(df_bt, use_container_width=True)
    st.markdown(f"**Average PnL:** `{df_bt['PnL'].mean():.2f}`")
    st.markdown(f"**Trap Trades:** `{(df_bt['Trap'].str.contains('⚠️')).sum()}` / {len(df_bt)}")
