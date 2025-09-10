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
st.title("🎯 Sniper Entry Dashboard – Tactical Mode")

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
# Strategy Recommendation Logic
# -------------------------------
def recommend_strategy(signal):
    if signal["bias"] == "Bullish" and "Bullish" in signal["ema"] and signal["pcr"] < 1:
        return "Bull Call Spread"
    elif signal["bias"] == "Bearish" and "Bearish" in signal["ema"] and signal["pcr"] > 1:
        return "Bear Put Spread"
    elif signal["bias"] == "Neutral" and signal["candle"] == "Doji" and 45 <= signal["rsi"] <= 55:
        return "Iron Condor"
    elif signal["rsi"] > 65 and signal["candle"] == "Bullish":
        return "Directional CE Buy"
    elif signal["rsi"] < 35 and signal["candle"] == "Bearish":
        return "Directional PE Buy"
    else:
        return "No Clear Strategy"

# -------------------------------
# Tactical Signal Engine
# -------------------------------
def generate_signal():
    bias = random.choice(["Bullish", "Bearish", "Neutral"])
    ema_crossover = random.choice(["Bullish Crossover", "Bearish Crossover", "No Signal"])
    pcr = round(random.uniform(0.6, 1.4), 2)
    candle = random.choice(["Hammer", "Doji", "Engulfing", "Bullish", "Bearish"])
    spot = random.randint(54000, 54500)
    rsi = random.randint(st.session_state.auto_tuner["rsi_min"], st.session_state.auto_tuner["rsi_max"])

    trap_trade = (bias == "Bullish" and pcr > 1.2 and candle == "Doji") or \
                 (bias == "Bearish" and pcr < 0.8 and candle == "Hammer")

    signal = {
        "bias": bias,
        "ema": ema_crossover,
        "pcr": pcr,
        "candle": candle,
        "spot": spot,
        "rsi": rsi,
        "trap": trap_trade
    }
    signal["strategy"] = recommend_strategy(signal)
    return signal

# -------------------------------
# Trade Logging Function
# -------------------------------
def log_trade(signal, result, points):
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    entry_time = now.strftime("%d-%b %I:%M %p")
    exit_time = now.strftime("%d-%b %I:%M %p")

    st.session_state.trade_journal.append({
        "Entry": entry_time,
        "Exit": exit_time,
        "Bias": signal["bias"],
        "EMA": signal["ema"],
        "PCR": signal["pcr"],
        "RSI": signal["rsi"],
        "Candle": signal["candle"],
        "Spot": signal["spot"],
        "Trap": signal["trap"],
        "Strategy": signal["strategy"],
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

    # Telegram Alert
    alert_msg = f"""
🎯 *Entry Signal – BankNifty*  
Bias: {signal['bias']}  
EMA: {signal['ema']}  
PCR: {signal['pcr']}  
RSI: {signal['rsi']}  
Candle: {signal['candle']}  
Spot: {signal['spot']}  
Strategy: {signal['strategy']}  
Trap Trade: {'Yes' if signal['trap'] else 'No'}  
Lot Size: {LOT_SIZE} | Capital: ₹{CAPITAL}  
Time: {entry_time}
"""
    send_telegram_alert(alert_msg)

# -------------------------------
# UI Panels
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
# Trade Trigger
# -------------------------------
if st.button("🔫 Generate Tactical Signal"):
    signal = generate_signal()
    result = random.choice(["Win", "Loss"])
    points = random.randint(60, 120) if result == "Win" else random.randint(-80, -30)
    log_trade(signal, result, points)
    st.success("Signal generated, strategy recommended, trade logged, and alert sent!")
