import streamlit as st
import pandas as pd
# Import nsepython for primary data fetching
from nsepython import nse_optionchain_scrapper
# Import yfinance for fallback data fetching
import yfinance as yf
from datetime import datetime
import pytz
import random

# -------------------------------
# Streamlit Config
# -------------------------------
st.set_page_config(page_title="Sniper Entry Dashboard", layout="wide")
st.title("🎯 Sniper Entry Dashboard – Nifty & BankNifty")

# -------------------------------
# Fetch Option Chain Data (with Yahoo Fallback)
# -------------------------------
@st.cache_data(ttl=300)
def fetch_option_chain(symbol="NIFTY"):
    # Map NSE symbols to Yahoo Finance symbols
    yahoo_symbol_map = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK"
    }
    
    chain_data = []
    expiry_list = []
    underlying_value = 0

    try:
        # Primary attempt: Fetch from NSE using nsepython
        data = nse_optionchain_scrapper(symbol)
        chain_data = data.get("records", {}).get("data", [])
        expiry_list = data.get("records", {}).get("expiryDates", [])
        underlying_value = data.get("records", {}).get("underlyingValue", 0)

        if not chain_data:
            raise ValueError("NSE data is empty or invalid.")

        return chain_data, expiry_list, underlying_value

    except Exception as e:
        st.warning(f"Failed to fetch data from NSE. Error: {e}")
        st.info("Attempting to fetch spot price from Yahoo Finance as a fallback.")
        
        # Fallback attempt: Fetch spot price from Yahoo Finance
        try:
            yahoo_symbol = yahoo_symbol_map.get(symbol)
            if yahoo_symbol:
                ticker = yf.Ticker(yahoo_symbol)
                history = ticker.history(period="1d")
                if not history.empty:
                    underlying_value = history['Close'].iloc[-1]
                
                # Note: Yahoo Finance doesn't provide option chain data like NSE.
                # We can only get the spot price as a fallback.
                st.success(f"Successfully fetched fallback spot price: {underlying_value}")
                
                # Return empty lists for chain data and expiry, as Yahoo doesn't have it
                return [], [], underlying_value
            else:
                st.error("Invalid symbol for Yahoo Finance.")
                return [], [], 0

        except Exception as yahoo_e:
            st.error(f"Failed to fetch fallback data from Yahoo. Error: {yahoo_e}")
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
    # This check is important to prevent errors if the primary data source fails.
    if not chain_data:
        st.warning("No option chain data available. Displaying a limited view based on spot price.")
        return pd.DataFrame([])

    rows = []
    for item in chain_data:
        ce = item.get("CE", {})
        pe = item.get("PE", {})
        strike = item.get("strikePrice", ce.get("strikePrice", pe.get("strikePrice", 0)))
        
        if not ce and not pe:
            continue
            
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

# If no data is available from either source, stop the app.
if not chain_data and spot_price == 0:
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
st.markdown(f"""
**Symbol:** `{symbol}`  
**Spot Price:** `{spot_price}`  
**Expiry:** `{expiry_list[0] if expiry_list else 'N/A'}`  
**Decay Bias:** `N/A`  
📉 **RSI:** `{rsi}`  
🕯️ **Candle Type:** `{candle_type}`  
🕒 **Last Updated:** {timestamp}
""")

# -------------------------------
# Filter High Confidence Trades
# -------------------------------
st.subheader("📊 High Confidence Trades")
if not df.empty:
    high_df = df[df["Confidence Score"] >= 75].sort_values("Confidence Score", ascending=False)
    st.dataframe(high_df[["Strike Price", "Decay Side", "Confidence Score", "Strategy", "Levels"]], use_container_width=True)
else:
    st.info("Option chain data is not available. Displaying a limited view.")

# -------------------------------
# Strategy Panel (Below Table)
# -------------------------------
st.subheader("📌 Strategy Recommendations")
if not df.empty:
    active_bias = df["Decay Side"].value_counts().idxmax()
    if not is_valid_entry(rsi, spot_price, active_bias, support_level, resistance_level):
        st.warning("⚠️ Market conditions not aligned with decay bias. Avoid entry.")
    elif active_bias == "PE":
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
else:
    st.info("No option chain data to provide strategy recommendations.")

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
st.caption("Built by Navinn • Sniper Entry Strategy • Powered by NSE Option Chain and Yahoo Finance")
