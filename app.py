import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
import calendar

st.set_page_config(page_title="Live Decay Bias Analyzer", layout="wide")
st.title("📉 Live Decay Bias Analyzer – Bank Nifty & Nifty")

def get_last_tuesday(year, month):
    last_day = calendar.monthrange(year, month)[1]
    for day in range(last_day, 0, -1):
        date = datetime(year, month, day)
        if date.weekday() == 1:
            return date
    return datetime(year, month, last_day)

def get_next_tuesday(today):
    days_ahead = (1 - today.weekday() + 7) % 7
    return today + timedelta(days=days_ahead)

today = datetime.now()
expiry_bn = get_last_tuesday(today.year, today.month)
expiry_nf = get_next_tuesday(today)

def fetch_spot(symbol):
    url = f"https://www.nseindia.com/api/quote-derivative?symbol={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9"
    }
    try:
        r = requests.get(url, headers=headers)
        data = r.json()
        return float(data["underlyingValue"])
    except:
        return None

spot_bn = fetch_spot("BANKNIFTY") or 44850.25
spot_nf = fetch_spot("NIFTY") or 24948.25

def fetch_option_chain(symbol):
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9"
    }
    try:
        r = requests.get(url, headers=headers)
        data = r.json()["records"]["data"]
        rows = []
        for entry in data:
            strike = entry.get("strikePrice")
            ce = entry.get("CE", {})
            pe = entry.get("PE", {})
            ce_change = ce.get("changeinOpenInterest", 0)
            pe_change = pe.get("changeinOpenInterest", 0)
            ce_oi = ce.get("openInterest", 1)
            pe_oi = pe.get("openInterest", 1)
            ce_ratio = round(ce_change / ce_oi, 2) if ce_oi else 0
            pcr = round(pe_oi / ce_oi, 2) if ce_oi else 0
            decay = "PE" if pe_change > ce_change else "CE"
            rows.append({
                "Strike Price": strike,
                "P/C Ratio": pcr,
                "CE Ratio": ce_ratio,
                "CE Change": ce_change,
                "PE Change": pe_change,
                "Decay Rate": decay
            })
        return pd.DataFrame(rows)
    except:
        return pd.DataFrame()

def fetch_yahoo_chain(symbol):
    url = f"https://query2.finance.yahoo.com/v7/finance/options/{symbol}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers)
        data = r.json()["optionChain"]["result"][0]["options"][0]
        rows = []
        for ce, pe in zip(data.get("calls", []), data.get("puts", [])):
            strike = ce.get("strike", 0)
            ce_oi = ce.get("openInterest", 0)
            pe_oi = pe.get("openInterest", 0)
            ce_change = ce.get("change", 0)
            pe_change = pe.get("change", 0)
            ce_ratio = round(ce_change / ce_oi, 2) if ce_oi else 0
            pcr = round(pe_oi / ce_oi, 2) if ce_oi else 0
            decay = "PE" if pe_change > ce_change else "CE"
            rows.append({
                "Strike Price": strike,
                "P/C Ratio": pcr,
                "CE Ratio": ce_ratio,
                "CE Change": ce_change,
                "PE Change": pe_change,
                "Decay Rate": decay
            })
        return pd.DataFrame(rows)
    except:
        return pd.DataFrame()

df_bn = fetch_option_chain("BANKNIFTY")
if df_bn.empty or df_bn["CE Change"].sum() == 0:
    df_bn = fetch_yahoo_chain("^NSEBANK")

df_nf = fetch_option_chain("NIFTY")
if df_nf.empty or df_nf["CE Change"].sum() == 0:
    df_nf = fetch_yahoo_chain("^NSEI")

def detect_bias(df):
    bias_counts = df["Decay Rate"].value_counts()
    return "PE Decay Active" if bias_counts.get("PE", 0) > bias_counts.get("CE", 0) else "CE Decay Active"

bias_bn = detect_bias(df_bn)
bias_nf = detect_bias(df_nf)

def recommend_strategy(bias):
    if bias == "PE Decay Active":
        return "✅ Sell Put Options (Short Put)\n✅ Buy Call Options (Long Call)\n✅ Bull Call Spread"
    else:
        return "✅ Sell Call Options (Short Call)\n✅ Buy Put Options (Long Put)\n✅ Bear Put Spread"

strategy_bn = recommend_strategy(bias_bn)
strategy_nf = recommend_strategy(bias_nf)

ist = pytz.timezone("Asia/Kolkata")
now = datetime.now(ist)
timestamp = now.strftime("%d-%b-%Y %I:%M:%S %p")

st.markdown(f"#### ⏱️ Last updated at `{timestamp}`")

tab1, tab2 = st.tabs(["🟦 Bank Nifty", "🟥 Nifty"])

with tab1:
    st.markdown(f"### 📍 Spot Price: `{spot_bn}`")
    st.markdown(f"### 📅 Expiry Date: `{expiry_bn.strftime('%d-%b-%Y')}`")
    st.markdown(f"### 📊 Decay Bias: `{bias_bn}`")
    st.subheader("📊 Analysis")
    st.dataframe(df_bn, use_container_width=True)
    st.subheader("🎯 Trading Recommendations")
    for line in strategy_bn.split("\n"):
        st.markdown(f"- {line}")

with tab2:
    st.markdown(f"### 📍 Spot Price: `{spot_nf}`")
    st.markdown(f"### 📅 Expiry Date: `{expiry_nf.strftime('%d-%b-%Y')}`")
    st.markdown(f"### 📊 Decay Bias: `{bias_nf}`")
    st.subheader("📊 Analysis")
    st.dataframe(df_nf, use_container_width=True)
    st.subheader("🎯 Trading Recommendations")
    for line in strategy_nf.split("\n"):
        st.markdown(f"- {line}")
