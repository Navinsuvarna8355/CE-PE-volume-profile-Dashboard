import streamlit as st
import streater as stt
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import time
from datetime import datetime, timedelta

# --- Global Config and Endpoints ---
NSE_URL = "https://www.nseindia.com/api/option-chain-indices?symbol={}"
NSE_INDEX_URL = "https://www.nseindia.com/api/allIndices"
HEADERS = {
    "user-agent": "Mozilla/5.0 ...",
    "accept-language": "en-US,en;q=0.9",
    "accept-encoding": "gzip, deflate, br"
}
INDEX_SYMBOLS = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK"
}

# --- Data Fetchers with Fallback ---
def fetch_nse_spot(symbol):
    try:
        page = requests.get(NSE_INDEX_URL, headers=HEADERS, timeout=10)
        data = page.json()
        for idx in data['data']:
            if idx['index'] == f"NIFTY 50" if symbol == "NIFTY" else "NIFTY BANK":
                return idx['last'], True
    except Exception:
        pass
    return None, False

def fetch_yfinance_spot(symbol):
    try:
        tkr = yf.Ticker(INDEX_SYMBOLS[symbol])
        h = tkr.history(period='1d')
        return h['Close'][-1], True
    except Exception:
        return None, False

def get_spot(symbol):
    spot, ok = fetch_nse_spot(symbol)
    if not ok:
        spot, ok = fetch_yfinance_spot(symbol)
    return spot or 0.0

def fetch_nse_option_chain(symbol):
    try:
        url = NSE_URL.format(symbol)
        page = requests.get(url, headers=HEADERS, timeout=10)
        data = page.json()
        return data, "NSE"
    except Exception:
        return None, "NSE_ERROR"

def fetch_yfinance_option_chain(symbol):
    try:
        tkr = yf.Ticker(INDEX_SYMBOLS[symbol])
        expiry = tkr.options[0]
        chain = tkr.option_chain(expiry)
        return chain, expiry, "YFIN"
    except Exception:
        return None, None, "YFIN_ERROR"

# --- Main Data Fetch, Metrics, and Recommendation Pipeline ---
def pipeline(symbol):
    opt_chain, src = fetch_nse_option_chain(symbol)
    if opt_chain is None:
        option_chain, expiry, src = fetch_yfinance_option_chain(symbol)
        # flatten DataFrames and map fields here...
        ce_df, pe_df = option_chain.calls, option_chain.puts
    else:
        # Parse NSE JSON to ce_df, pe_df
        ce_rows, pe_rows = [], []
        expiry = opt_chain['records']['expiryDates'][0]
        for item in opt_chain['records']['data']:
            if 'CE' in item:
                ce_rows.append(item['CE'])
            if 'PE' in item:
                pe_rows.append(item['PE'])
        ce_df = pd.DataFrame(ce_rows)
        pe_df = pd.DataFrame(pe_rows)
    # Calculate all metrics
    spot = get_spot(symbol)
    ce_oi = ce_df['openInterest'].sum()
    pe_oi = pe_df['openInterest'].sum()
    ce_oi_chg = ce_df['changeinOpenInterest'].sum()
    pe_oi_chg = pe_df['changeinOpenInterest'].sum()
    ce_ratio = ce_oi_chg / (pe_oi_chg+1e-9)
    pcr = pe_oi / (ce_oi+1e-9)
    decay_bias = estimate_decay(ce_df, pe_df)
    strategy = suggest_strategy(pcr, ce_ratio, decay_bias)
    return {
        "spot": spot,
        "expiry": expiry,
        "pcr": pcr,
        "ce_ratio": ce_ratio,
        "decay_bias": decay_bias,
        "strategy": strategy,
        "ce_df": ce_df,
        "pe_df": pe_df,
        "src": src
    }

def estimate_decay(ce_df, pe_df):
    # Approximation: average (IV / days to expiry) over ATM options
    return np.mean((ce_df['impliedVolatility'] + pe_df['impliedVolatility']) / (ce_df['daysToExpiry'] + 1))

def suggest_strategy(pcr, ce_ratio, decay_bias):
    # Very simple placeholder logic
    if pcr > 1.2:
        return "Bullish Bias: Sell Puts / Bull Put Spread"
    elif ce_ratio > 1.1:
        return "Bearish Bias: Sell Calls / Bear Call Spread"
    elif abs(decay_bias) < 0.1:
        return "Neutral: Iron Condor or Short Strangle"
    else:
        return "No clear bias; Wait"

# --- Streamlit + Streater Dashboard ---
def dashboard(symbol="BANKNIFTY", refresh_seconds=60):
    st.set_page_config(page_title="Bank Nifty/Nifty Option Chain Dashboard", layout="wide")
    st.title(f"Live {symbol} Option Chain Dashboard")
    st.markdown("By [YourName] | Powered by NSE/Yahoo")
    st.markdown(f"### Data last updated: {datetime.now()} UTC")
    with st.spinner("Fetching live data..."):
        state = stt.use_state()
        if stt.should_refresh(interval_seconds=refresh_seconds):
            result = pipeline(symbol)
            state['data'] = result
        else:
            result = state.get('data', pipeline(symbol))
    # Display Spot, Expiry, Key Metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Spot Price", f"{result['spot']:.2f}")
    col2.metric("Expiry", result['expiry'])
    col3.metric("PCR", f"{result['pcr']:.2f}")
    col4.metric("CE Ratio", f"{result['ce_ratio']:.2f}")
    col5.metric("Decay Bias", f"{result['decay_bias']:.2f}")
    st.success(f"Recommended Strategy: {result['strategy']}")
    with st.expander("Show Option Chain Data"):
        st.write("CALLS", result['ce_df'])
        st.write("PUTS", result['pe_df'])
    st.caption(f"Data Source: {result['src']}")

if __name__ == "__main__":
    symbol = st.sidebar.selectbox("Select Instrument", ["BANKNIFTY", "NIFTY"])
    refresh_secs = st.sidebar.slider("Auto-refresh Interval (seconds)", 30, 300, 60, 30)
    dashboard(symbol, refresh_secs)
