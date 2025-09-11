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
CAPITAL = 10000
LOT_SIZE = 1

st.set_page_config(page_title="Sniper Dashboard", layout="wide")
st.title("🎯 Sniper Entry Dashboard – Phase 2")

# -------------------------------
# Telegram Alert Function
# -------------------------------
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        st.error(f"Telegram alert failed: {e}")

# -------------------------------
# Session State Initialization
# -------------------------------
if "trade_journal" not in st.session_state:
    st.session_state.trade_journal = []

if "pnl_tracker" not in st.session_state:
    st.session_state.pnl_tracker = []

if "auto_tuner" not in st.session_state:
    st.session_state.auto_tuner = {"rsi_min": 30, "rsi_max": 70}

# -------------------------------
# Trade Logging Function
# -------------------------------
def log_trade(entry_time, exit_time, bias, strike, rsi, candle, strategy, result, points):
    st.session_state.trade_journal.append({
        "Entry": entry_time,
        "Exit": exit_time,
        "Bias": bias,
        "Strike": strike,
        "RSI": rsi,
        "Candle": candle,
        "Strategy": strategy,
        "Result": result,
        "Points": points
    })
    st.session_state.pnl_tracker.append(points)

    # Auto-tuner logic
    if result == "Loss":
        st.session_state.auto_tuner["rsi_min"] += 1
        st.session_state.auto_tuner["rsi_max"] -= 1
    elif result == "Win":
        st.session_state.auto_tuner["rsi_min"] = max(25, st.session_state.auto_tuner["rsi_min"] - 1)
        st.session_state.auto_tuner["rsi_max"] = min(75, st.session_state.auto_tuner["rsi_max"] + 1)

# -------------------------------
# Display Panels
# -------------------------------
st.subheader("📘 Trade Journal")
if st.session_state.trade_journal:
    journal_df = pd.DataFrame(st.session_state.trade_journal)
    st.dataframe(journal_df, use_container_width=True)

st.subheader("📊 P&L Tracker")
if st.session_state.pnl_tracker:
    pnl_df = pd.DataFrame({"Points": st.session_state.pnl_tracker})
    st.line_chart(pnl_df)
    total = sum(st.session_state.pnl_tracker)
    accuracy = round((sum(1 for p in st.session_state.pnl_tracker if p > 0) / len(st.session_state.pnl_tracker)) * 100, 2)
    st.markdown(f"**Total Points:** `{total}` | **Accuracy:** `{accuracy}%`")

st.subheader("🧠 Auto-Tuner Status")
rsi_min = st.session_state.auto_tuner["rsi_min"]
rsi_max = st.session_state.auto_tuner["rsi_max"]
st.markdown(f"**RSI Thresholds:** `{rsi_min}` to `{rsi_max}`")

# -------------------------------
# Simulated Trade Trigger
# -------------------------------
if st.button("🔫 Simulate Trade"):
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    entry_time = now.strftime("%d-%b %I:%M %p")
    exit_time = now.strftime("%d-%b %I:%M %p")
    bias = random.choice(["PE", "CE"])
    strike = random.choice([54200, 54300, 54400])
    rsi = random.randint(rsi_min, rsi_max)
    candle = random.choice(["Doji", "Hammer", "Engulfing", "Bullish", "Bearish"])
    strategy = "Bear Put Spread" if bias == "PE" else "Bull Call Spread"
    result = random.choice(["Win", "Loss"])
    points = random.randint(60, 120) if result == "Win" else random.randint(-80, -30)

    log_trade(entry_time, exit_time, bias, strike, rsi, candle, strategy, result, points)

    alert_msg = f"""
🎯 *Entry Signal – BankNifty*  
Bias: {bias} Decay Active  
Strike: {strike}  
RSI: {rsi}  
Candle: {candle}  
Strategy: {strategy}  
SL: {strike + 100 if bias == 'PE' else strike - 100}  
Target: {strike - 150 if bias == 'PE' else strike + 150}  
Lot Size: {LOT_SIZE} | Capital: ₹{CAPITAL}  
Time: {entry_time}
"""
    send_telegram_alert(alert_msg)
    st.success("Trade logged and alert sent!")
