# options_decay_dashboard.py
# Streamlit Dashboard for Options Decay Bias Analysis and Strategy Recommendations

import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ============================
# Spot Price Input Module
# ============================
st.header("Spot Price Input")
spot_price = st.number_input("Enter Spot Price:", min_value=0.0, format="%.2f")

# ============================
# Expiry Date Selection Module
# ============================
st.header("Expiry Date Selection")
expiry_date = st.date_input("Select Expiry Date:")

# ============================
# CE/PE Theta Table Module
# ============================
st.header("CE/PE Theta Table")
ce_theta = st.number_input("Enter CE Theta value:", format="%.4f")
pe_theta = st.number_input("Enter PE Theta value:", format="%.4f")

theta_table = pd.DataFrame({
    "Option Type": ["Call (CE)", "Put (PE)"],
    "Theta": [ce_theta, pe_theta]
})
st.table(theta_table)

# ============================
# Decay Bias Detection Algorithm
# ============================
st.header("Decay Bias Detection")

decay_bias = ""
if ce_theta < pe_theta:
    decay_bias = "PUTS are decaying slower than CALLS"
elif ce_theta > pe_theta:
    decay_bias = "CALLS are decaying slower than PUTS"
else:
    decay_bias = "CE and PE have equal decay rate"

st.write(f"Decay Bias Detected: **{decay_bias}**")

# ============================
# Strategy Recommendation Engine
# ============================
st.header("Strategy Recommendation")

recommended_strategy = ""
if decay_bias == "PUTS are decaying slower than CALLS":
    recommended_strategy = "Bull Call Spread or Short Put"
elif decay_bias == "CALLS are decaying slower than PUTS":
    recommended_strategy = "Bear Put Spread or Long Call"
else:
    recommended_strategy = "Neutral Strategy (e.g., Iron Condor)"

st.write(f"Recommended Strategy: **{recommended_strategy}**")

# ============================
# Timestamp Display and Auto-refresh
# ============================
st.header("Last Update Timestamp")
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.write(f"Updated on: **{timestamp}**")

# ============================
# Optional: Telegram Alert Integration
# ============================
st.header("Telegram Alert (Optional)")

telegram_enabled = st.checkbox("Enable Telegram Alerts")

if telegram_enabled:
    telegram_token = st.text_input("Enter your Telegram Bot Token")
    telegram_chat_id = st.text_input("Enter your Telegram Chat ID")

    message = (
        f"Decay Bias: {decay_bias}\n"
        f"Strategy Recommendation: {recommended_strategy}\n"
        f"Spot Price: {spot_price}\n"
        f"Expiry Date: {expiry_date}\n"
        f"Timestamp: {timestamp}"
    )

    if st.button("Send Telegram Alert"):
        send_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        params = {
            "chat_id": telegram_chat_id,
            "text": message
        }
        response = requests.post(send_url, data=params)
        if response.status_code == 200:
            st.success("Alert sent successfully!")
        else:
            st.error("Failed to send alert.")

# End of options_decay_dashboard.py
