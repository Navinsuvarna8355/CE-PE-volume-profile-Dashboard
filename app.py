import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import random

# -------------------------------
# Streamlit Config
# -------------------------------
st.set_page_config(page_title="Sniper Entry Dashboard", layout="wide")
st.title("🎯 Sniper Entry Dashboard – Nifty & BankNifty")

# -------------------------------
# Fetch Option Chain Data
# -------------------------------
@st.cache_data(ttl=300)
def fetch_option_chain(symbol="NIFTY"):
    try:
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com"
        }
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers)
        response = session.get(url, headers=headers)
        data = response.json()
        return data["records"]["data"], data["records"]["expiryDates"], data["records"]["underlyingValue"]
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return [], [], 0

# -------------------------------
# Simulated RSI & Support/Resistance
# -------------------------------
def get_market_indicators(symbol, spot_price):
    rsi = random.randint(25, 75)
    support = spot_price - 100
    resistance = spot_price + 100
    candle_type = random.choice(["bullish", "bearish", "doji", "hammer", "engulfing"])
    momentum_drop = random.choice([True, False])
    return rsi, support, resistance, candle_type, momentum_drop

# -------------------------------
# Entry Validation Logic
# -------------------------------
def is_valid_entry(rsi, spot_price, decay_side, support, resistance):
    if decay_side == "PE" and spot_price > support:
        return False
    if decay_side == "CE" and spot_price < resistance:
        return False
    if rsi < 30 and decay_side == "PE":
        return False
    if rsi > 70 and decay_side == "CE":
        return False
    return True

# -------------------------------
# Exit Signal Logic
# -------------------------------
def should_exit_trade(candle_type, momentum_drop, current_hour, spot_price, resistance):
    if candle_type in ["doji", "hammer", "engulfing"] and momentum_drop:
        return True
    if current_hour >= 13 and spot_price > resistance:
        return True
    return False

# -------------------------------
# Confidence Score Logic
# -------------------------------
def calculate_confidence(row, spot_price):
    decay_score = 30 if row["Decay Side"] == "PE" else 30 if row["Decay Side"] == "CE" else 10
    price_zone_score = 30 if abs(row["Strike Price"] - spot_price) <= 100 else 10
    volume_score = random.randint(20, 40)
    return decay_score + price_zone_score + volume_score

def generate_strategy(row):
    if row["Confidence Score"] >= 75:
        if row["Decay Side"] == "PE":
            return "🔴 Bear Put Spread or Long Put"
        elif row["Decay Side"] == "CE":
            return "🟢 Bull Call Spread or Long Call"
        else:
            return "🟡 Iron Condor or Straddle"
    else:
        return "⏸️ Wait – Low conviction"

def generate_levels(row):
    strike = row["Strike Price"]
    return f"🎯 Entry: {strike} • SL: {strike + 100} • Target: {strike - 150}" if row["Decay Side"] == "PE" else \
           f"🎯 Entry: {strike} • SL: {strike - 100} • Target: {strike + 150}"

# -------------------------------
# Process Data
# -------------------------------
def process_data(chain_data, spot_price):
    rows = []
    for item in chain_data:
        ce = item.get("CE", {})
        pe = item.get("PE", {})
        strike = item.get("strikePrice", ce.get("strikePrice", pe.get("strikePrice", 0)))
        ce_theta = ce.get("theta", 0)
        pe_theta = pe.get("theta", 0)
        ce_change = ce.get("change", 0)
        pe_change = pe.get("change", 0)
        decay_side = "CE" if ce_theta < pe_theta else "PE"
        confidence = calculate_confidence({
            "Strike Price": strike,
            "Decay Side": decay_side
        }, spot_price)
        strategy = generate_strategy({
            "Strike Price": strike,
            "Decay Side": decay_side,
            "Confidence Score": confidence
        })
        levels = generate_levels({
            "Strike Price": strike,
            "Decay Side": decay_side
        })
        rows.append({
            "Strike Price": strike,
            "CE Theta": ce_theta,
            "PE Theta": pe_theta,
            "CE Change": ce_change,
            "PE Change": pe_change,
            "Decay Side": decay_side,
            "Confidence Score": confidence,
            "Strategy": strategy,
            "Levels": levels
        })
    return pd.DataFrame(rows)

# -------------------------------
# UI Controls
# -------------------------------
symbol = st.sidebar.selectbox("Symbol", ["NIFTY", "BANKNIFTY"])
st.sidebar.markdown("⏱️ Auto-refresh every 5 minutes")
refresh = st.sidebar.button("🔄 Manual Refresh")

# -------------------------------
# Main Execution
# -------------------------------
chain_data, expiry_list, spot_price = fetch_option_chain(symbol)
if not chain_data:
    st.stop()

rsi, support_level, resistance_level, candle_type, momentum_drop = get_market_indicators(symbol, spot_price)
df = process_data(chain_data, spot_price)

# Timestamp in IST
ist = pytz.timezone("Asia/Kolkata")
now = datetime.now(ist)
timestamp = now.strftime("%A, %d %B %Y • %I:%M %p")
current_hour = now.hour

# -------------------------------
# Display Header Info
# -------------------------------
active_bias = df["Decay Side"].value_counts().idxmax()

st.markdown(f"""
**Symbol:** `{symbol}`  
**Spot Price:** `{spot_price}`  
**Expiry:** `{expiry_list[0]}`  
**Decay Bias:** `{active_bias} Decay Active`  
📉 **RSI:** `{rsi}`  
🕯️ **Candle Type:** `{candle_type}`  
🕒 **Last Updated:** {timestamp}
""")

# -------------------------------
# Filter High Confidence Trades
# -------------------------------
st.subheader("📊 High Confidence Trades")
high_df = df[df["Confidence Score"] >= 75].sort_values("Confidence Score", ascending=False)
st.dataframe(high_df[["Strike Price", "Decay Side", "Confidence Score", "Strategy", "Levels"]], use_container_width=True)

# -------------------------------
# Strategy Panel (Below Table)
# -------------------------------
st.subheader("📌 Strategy Recommendations")

if not is_valid_entry(rsi, spot_price, active_bias, support_level, resistance_level):
    st.warning("⚠️ Market conditions not aligned with decay bias. Avoid entry.")
else:
    if active_bias == "PE":
        st.markdown("""
#### 🔴 Bearish Bias (Downside)
- Put options are decaying faster than calls.
- RSI confirms bearish zone.
- Consider strategies:
    - 📌 Bear Put Spread
    - 📌 Long Put
    - 📌 CE Shorting (if CE IV is high)
""")
    elif active_bias == "CE":
        st.markdown("""
#### 🟢 Bullish Bias (Upside)
- Call options are decaying faster than puts.
- RSI confirms bullish zone.
- Consider strategies:
    - 📌 Bull Call Spread
    - 📌 Long Call
    - 📌 PE Shorting (if PE IV is high)
""")
    else:
        st.markdown("""
#### 🟡 Neutral Bias (Range-bound)
- Low decay on both CE and PE.
- Consider strategies:
    - 📌 Iron Condor
    - 📌 Straddle
    - 📌 Butterfly Spread
""")

# -------------------------------
# Exit Signal Log
# -------------------------------
st.subheader("📤 Exit Signal Log")
if should_exit_trade(candle_type, momentum_drop, current_hour, spot_price, resistance_level):
    st.warning(f"""
⏱️ Time: {timestamp}  
📉 Reason: Reversal candle + momentum drop + spot breakout  
✅ Action: Exit trade / Avoid fresh entry
""")
else:
    st.success("✅ No exit signal triggered. Trade bias still valid.")

# -------------------------------
# Footer
# -------------------------------
st.markdown("---")
st.caption("Built by Navinn • Sniper Entry Strategy • Powered by NSE Option Chain")
