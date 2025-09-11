import streamlit as st
import pandas as pd
from nsepython import nse_optionchain_scrapper
import yfinance as yf
from datetime import datetime
import pytz
import random
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
    yahoo_symbol_map = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK"
    }
    
    chain_data = []
    expiry_list = []
    underlying_value = 0

    try:
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
        
        try:
            yahoo_symbol = yahoo_symbol_map.get(symbol)
            if yahoo_symbol:
                ticker = yf.Ticker(yahoo_symbol)
                history = ticker.history(period="1d")
                if not history.empty:
                    underlying_value = history['Close'].iloc[-1]
                
                st.success(f"Successfully fetched fallback spot price: {underlying_value}")
                
                return [], [], underlying_value
            else:
                st.error("Invalid symbol for Yahoo Finance.")
                return [], [], 0

        except Exception as yahoo_e:
            st.error(f"Failed to fetch fallback data from Yahoo. Error: {yahoo_e}")
            return [], [], 0

# -------------------------------
# Main Execution
# -------------------------------

# Sidebar Controls
with st.sidebar:
    st.header("Settings")
    symbol = st.selectbox("Index", ["NIFTY", "BANKNIFTY"])
    auto_refresh = st.checkbox("Auto Refresh", value=True)
    refresh_interval = st.slider("Refresh Interval (s)", 30, 600, 60)
    fetch_now = st.button("Fetch Now")

# Auto-refresh logic
if auto_refresh and not fetch_now:
    st.rerun(refresh_interval)

if fetch_now:
    st.cache_data.clear()
    st.rerun()

chain_data, expiry_list, spot_price = fetch_option_chain(symbol)

# --- Top Header Section ---
col1, col2, col3 = st.columns(3)
col1.metric("Nifty Spot Price", f"{spot_price:.2f}")
col2.metric("Expiry Date", expiry_list[0] if expiry_list else "N/A")

if chain_data:
    df_temp = pd.DataFrame(chain_data)
    pe_decay = df_temp["PE"].apply(lambda x: x.get("theta", 0))
    ce_decay = df_temp["CE"].apply(lambda x: x.get("theta", 0))
    decay_bias = "CE Decay Active" if ce_decay.mean() < pe_decay.mean() else "PE Decay Active"
else:
    decay_bias = "N/A"

col3.metric("Decay Bias", decay_bias)
st.write(f"Last updated: {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%H:%M:%S IST')}")

# --- Main Analysis Section ---
st.subheader("Analysis")
tab1, tab2 = st.tabs(["Data Table", "Theta Chart"])

with tab1:
    if chain_data:
        df_rows = []
        for item in chain_data:
            strike = item.get("strikePrice")
            ce = item.get("CE", {})
            pe = item.get("PE", {})
            
            df_rows.append({
                "Strike Price": strike,
                "CE Theta": ce.get("theta", 0),
                "PE Theta": pe.get("theta", 0),
                "CE Change": ce.get("change", 0),
                "PE Change": pe.get("change", 0),
                "Decay Side": "CE" if ce.get("theta", 0) < pe.get("theta", 0) else "PE"
            })
        
        df = pd.DataFrame(df_rows)
        st.dataframe(df.sort_values("Strike Price"))
    else:
        st.warning("No option chain data available to display.")

with tab2:
    if chain_data:
        strikes = [item['strikePrice'] for item in chain_data]
        ce_theta = [item.get('CE', {}).get('theta', 0) for item in chain_data]
        pe_theta = [item.get('PE', {}).get('theta', 0) for item in chain_data]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=strikes, y=ce_theta, mode='lines+markers', name='CE Theta'))
        fig.add_trace(go.Scatter(x=strikes, y=pe_theta, mode='lines+markers', name='PE Theta'))
        fig.update_layout(title='Theta vs. Strike Price', xaxis_title='Strike Price', yaxis_title='Theta', legend_title='Option Type')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No option chain data to generate the Theta Chart.")

# --- Trading Recommendations Section ---
st.header("Trading Recommendations")

if decay_bias == "CE Decay Active":
    st.info("These suggestions are based on decay bias. Always use additional analysis.")
    st.subheader("Bearish Bias (Downside)")
    st.write("Call options are decaying faster than puts. Consider bearish strategies:")
    st.markdown("""
- Sell Call Options (Short Call)
- Buy Put Options (Long Put)
- Bear Put Spread
""")
elif decay_bias == "PE Decay Active":
    st.info("These suggestions are based on decay bias. Always use additional analysis.")
    st.subheader("Bullish Bias (Upside)")
    st.write("Put options are decaying faster than calls. Consider bullish strategies:")
    st.markdown("""
- Sell Put Options (Short Put)
- Buy Call Options (Long Call)
- Bull Call Spread
""")
else:
    st.info("Market is likely neutral or data is unavailable. No strong decay bias detected.")
