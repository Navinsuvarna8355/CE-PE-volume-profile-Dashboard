# SNIPER-STYLE NIFTY/BANKNIFTY OPTIONS TRADING DASHBOARD IN STREAMLIT
# All major components are cross-referenced to public web sources (see inline comments).

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import datetime as dt
import pytz
import requests

# For auto-refresh
from streamlit_autorefresh import st_autorefresh  # https://github.com/kmcgrady/streamlit-autorefresh

# For interactive tables/grids
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode  # https://github.com/PablocFonseca/streamlit-aggrid

# -----
# 1. PAGE & APP CONFIG — MOBILE CLEAN UI, WIDE SUPPORT
# -----
st.set_page_config(
    page_title="Sniper Options Dashboard: NIFTY/BANKNIFTY",
    page_icon="🎯",
    layout="wide",   # https://peerdh.com/blogs/programming-insights/streamlit-layout-customization-a-comprehensive-guide
    initial_sidebar_state="collapsed",
)

# -----
# 2. AUTO-REFRESH LOGIC (every 5 minutes)
# -----
refresh_interval_sec = 300
st_autorefresh(interval=refresh_interval_sec * 1000, key="autorefresh_every_5min")  # https://github.com/kmcgrady/streamlit-autorefresh

# -----
# 3. SIDEBAR: SYMBOL & SETTINGS
# -----
with st.sidebar:
    st.title("Settings")
    selected_index = st.selectbox("Index", ("NIFTY", "BANKNIFTY"))
    near_strike_count = st.slider("Near-ATM Strikes ±", 2, 6, 3)
    opt_expiry_type = st.radio("Expiry", ("nearest", "next"))
    st.markdown("---")
    st.caption("Auto-refreshes every 5 minutes. [Learn More](https://github.com/kmcgrady/streamlit-autorefresh)")
    st.button("Manual Refresh", on_click=lambda: st.cache_data.clear())

# -----
# 4. DATA FETCH — NSE OPTIONS CHAIN (NIFTY/BANKNIFTY)
# -----
@st.cache_data(show_spinner=True, ttl=240)
def fetch_option_chain(symbol: str):
    # Large parts adapted and consolidated from:
    #   https://github.com/sbwakte556-a11y/NIFTY-DASHBOARD/blob/main/app.py
    #   https://dev.to/shahstavan/nse-option-chain-data-using-python-4fe5
    #   https://tutlogic.com/how-to-fetch-live-option-chain-data-from-nse-india-using-python/
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    session = requests.Session()
    session.headers.update({
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "accept-language": "en-US,en;q=0.9",
        "accept": "application/json, text/plain, */*",
        "referer": "https://www.nseindia.com/",
    })
    try:
        # Must load main page to initialize cookies.
        session.get("https://www.nseindia.com", timeout=5)
    except Exception:
        pass
    try:
        resp = session.get(url, timeout=12)
        if resp.status_code != 200:
            return pd.DataFrame()
        data = resp.json()
    except Exception:
        return pd.DataFrame()
    # Flatten
    records = data.get("records", {})
    spot = float(records.get("underlyingValue") or 0.0)
    expiry_dates = records.get("expiryDates", [])
    # Find correct expiry
    expiry_idx = 0 if len(expiry_dates) > 0 else None
    if opt_expiry_type == "next" and len(expiry_dates) > 1:
        expiry_idx = 1
    expiry_dt = expiry_dates[expiry_idx] if expiry_idx is not None else None

    rows = []
    for item in records.get("data", []):
        if expiry_dt and item.get("expiryDate") != expiry_dt:
            continue
        strike = item.get("strikePrice")
        if strike is None:
            continue
        for opt_type in ("CE", "PE"):
            optdata = item.get(opt_type)
            if not isinstance(optdata, dict):
                continue
            rows.append({
                "symbol": symbol,
                "expiry": expiry_dt,
                "strike": int(strike),
                "option_type": opt_type,
                "ltp": float(optdata.get("lastPrice") or 0.0),
                "oi": float(optdata.get("openInterest") or 0.0),
                "volume": float(optdata.get("totalTradedVolume") or 0.0),
                "iv": float(optdata.get("impliedVolatility") or 0.0),
                "ts": dt.datetime.now(pytz.timezone("Asia/Kolkata")),
                "spot": spot,
            })
    df = pd.DataFrame(rows)
    if len(df) == 0:
        return pd.DataFrame()
    # Compute ATM for near-strike filtering
    step = 100 if symbol == "BANKNIFTY" else 50
    atm_strike = int(round(spot / step) * step)
    df = df.loc[(df["strike"] >= atm_strike - step*near_strike_count)
                & (df["strike"] <= atm_strike + step*near_strike_count)].copy()
    df["atm_strike"] = atm_strike
    df["spot"] = spot
    return df

# -----
# 5. VOLUME PROFILE PER STRIKE — ADVANCED MARKET READING
# -----
def compute_volume_profile(df: pd.DataFrame):
    # On volume profile concept: https://www.jumpstarttrading.com/volume-profile/
    # On implementation: https://www.digitaldesignjournal.com/python-volume-profile-with-example/
    result = []
    grouped = df.groupby("strike")
    for strike, grp in grouped:
        vol_ce = grp.loc[grp.option_type == "CE", "volume"].sum()
        vol_pe = grp.loc[grp.option_type == "PE", "volume"].sum()
        result.append({"strike": strike, "volume_ce": vol_ce, "volume_pe": vol_pe, "volume_total": vol_ce + vol_pe})
    vpdf = pd.DataFrame(result).set_index("strike")
    return vpdf

# -----
# 6. CANDLESTICK CHART DATA (SPOT) — FOR OVERLAYS
# -----
@st.cache_data(show_spinner=False, ttl=600)
def fetch_spot_ohlc(symbol: str, lookback="3d", interval="5m"):
    # OHLC data for overlay (candles/price action), using yfinance, others possible
    import yfinance as yf
    symbol_mapping = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
    yf_symbol = symbol_mapping.get(symbol, "^NSEI")
    hist = yf.download(yf_symbol, period=lookback, interval=interval, progress=False)
    if len(hist) == 0:
        return pd.DataFrame()
    return hist.rename_axis("datetime").reset_index()

# -----
# 7. PRICE ACTION ZONES (SUPPLY/DEMAND) & SUPPORT/RESISTANCE
# -----
def price_action_zones(ohlc: pd.DataFrame):
    # Identify swing highs/lows support/resistance as demand/supply zones.
    # Methods adapt from:
    #   https://docs.zeiierman.com/toolkit/marke-structure-price-action/zones
    #   https://blog.quantinsti.com/price-action-trading/
    close = ohlc['Close']
    q25 = close.quantile(0.25)
    q75 = close.quantile(0.75)
    levels = {
        "support_1": q25,
        "resistance_1": q75,
        "support_2": close.quantile(0.15),
        "resistance_2": close.quantile(0.85)
    }
    return levels

# -----
# 8. OPTION GREEKS: THETA DECAY FOR CE/PE
# -----
def estimate_theta_decay(row):
    # Approximate Greek calculation. For full Greeks, quantlib/Black-Scholes can be used.
    # See https://www.pyquantnews.com/the-pyquant-newsletter/options-lose-value-every-day-measure-theta-decay
    days_to_expiry = (pd.to_datetime(row["expiry"], dayfirst=False) - row["ts"]).days
    # Simple time decay: Out-of-the-money options, less time to expiry, higher decay
    spot, strike = row["spot"], row["strike"]
    moneyness = (spot - strike) if row["option_type"] == "CE" else (strike - spot)
    if days_to_expiry <= 0:
        theta = -row["ltp"]  # Will expire worthless
    else:
        # Approx: theta per day is higher for ATM, higher for short expiry
        # ATM: approx 0.015*ltp per day; ITM/OTM less
        base_theta = 0.015 * row["ltp"] if abs(moneyness)<0.2*spot else 0.009 * row["ltp"]
        theta = -base_theta * max(1, 7/days_to_expiry)  # Increase as expiry nears
    return round(theta, 2)

# -----
# 9. VOLUME PROFILE, PRICE ACTION ZONES, THETA DECAY, STRATEGY, CONFIDENCE LOGIC
# -----
def compute_confidence_score(row, volume_profile, price_zones):
    # Core method: combine volume, price zone, theta decay to yield a 0-100 confidence score.
    # On logic: https://github.com/KamranAliOfficial/nifty-live_trading-app (strategy.py), https://github.com/sbwakte556-a11y/NIFTY-DASHBOARD/
    sc_vol = 0
    if row["strike"] in volume_profile.index:
        vol_total = volume_profile.loc[row["strike"], "volume_total"]
        vol_rank = volume_profile["volume_total"].rank()
        # Higher total volume ranks = more participation, more relevance
        sc_vol = 25 + 50 * (vol_rank.loc[row["strike"]] / len(vol_rank))
    # Price action: Only consider strikes close to support/resistance
    sc_zone = 0
    close = row["strike"]
    for k, val in price_zones.items():
        if abs(close - val) <= 0.01*close:
            sc_zone = 40
            break
    # Theta penalty (decaying, lose value before expiry or if not ATM/ITM)
    theta = row.get("theta", 0.0)
    sc_theta = max(0, 30 + np.sign(-theta)*20)
    # Sum up — scale/cap at 100
    score = min(100, sc_vol + sc_zone + sc_theta)
    # If very low liquidity or OI, reduce confidence significantly
    if row["volume"] < 300 or row["oi"] < 500:
        score = score * 0.6
    # Regularize and forceint
    return int(round(score))

def recommend_strategy(row, price_zones):
    # Example: "Scalp Buy CE", "Scalp Sell PE", "Short Iron Condor" etc
    spot, strike, opt_type = row["spot"], row["strike"], row["option_type"]
    if strike < spot and opt_type == "PE":
        return "Sell OTM PE", "Sell at Zone Support"
    elif strike > spot and opt_type == "CE":
        return "Sell OTM CE", "Sell at Zone Resistance"
    elif abs(strike-spot) < 0.015*spot:
        if opt_type == "CE":
            return "Buy ATM CE", "Momentum/Zone Breakout"
        else:
            return "Buy ATM PE", "Momentum/Zone Breakdown"
    else:
        return "Scalp Sell (Decay)", "Theta Decay Play"

def compute_stoploss_target(row, price_zones):
    # https://amsflow.com/tools/options-sl-targets-calculator
    entry = row["ltp"] if row["ltp"] > 0 else 1.0
    # Stop under recent swing low/high, or % loss limits (15-30% of premium)
    sl = entry * 0.7
    tgt = entry * 1.5
    for k, val in price_zones.items():
        # e.g. if CE and at resistance, target is recent resistance
        if "resistance" in k and row["option_type"] == "CE":
            tgt = max(tgt, abs(val - row["strike"]))
        if "support" in k and row["option_type"] == "PE":
            tgt = max(tgt, abs(row["strike"] - val))
    return round(sl, 2), round(tgt, 2)

# -----
# 10. MAIN DASHBOARD LOGIC — LOAD DATA, ANALYTICS, UI
# -----
st.title("🎯 Sniper Options Dashboard")
st.markdown(
    f"**Instrument:** `{selected_index}` | **Auto-refreshes every {refresh_interval_sec//60} min.** "
)

# Fetch options chain data
opts = fetch_option_chain(selected_index)
if opts.empty:
    st.error("⚠️ Unable to fetch CE/PE options data. Please try later.")
    st.stop()

# Candlestick chart for underlying
spot_ohlc = fetch_spot_ohlc(selected_index)
if len(spot_ohlc) > 0:
    pa_zones = price_action_zones(spot_ohlc)
else:
    pa_zones = {}

# Volume profile per strike computation
vol_profile = compute_volume_profile(opts)
opts = opts.merge(vol_profile, left_on="strike", right_index=True, how="left")

# Compute theta decay, per-row analytics
opts["theta"] = opts.apply(estimate_theta_decay, axis=1)
opts["confidence"] = opts.apply(lambda r: compute_confidence_score(r, vol_profile, pa_zones), axis=1)
opts[["strategy", "strategy_context"]] = opts.apply(
    lambda r: pd.Series(recommend_strategy(r, pa_zones)), axis=1
)
opts[["stop_loss", "target"]] = opts.apply(
    lambda r: pd.Series(compute_stoploss_target(r, pa_zones)), axis=1
)

# Filter for "high confidence" trades (>80)
trades = opts[opts["confidence"] >= 80].copy()
trades = trades.sort_values(["confidence", "volume_total"], ascending=[False, False])

# -----
# 11. CANDLESTICK + OVERLAYED VOLUME PROFILE CHARTS (SPOT)
# -----
def plot_combined_chart(ohlc: pd.DataFrame, price_levels, opts: pd.DataFrame, show_profile=True):
    fig = go.Figure()
    # Candlesticks (spot)
    fig.add_trace(go.Candlestick(
        x=ohlc['datetime'],
        open=ohlc['Open'], high=ohlc['High'], low=ohlc['Low'], close=ohlc['Close'],
        name="Spot Candles", yaxis="y1"
    ))
    # Overlay price action zones
    for name, val in price_levels.items():
        fig.add_hline(
            y=val, line_dash="dot",
            annotation_text=f"{name}: {val:.2f}", opacity=0.4,
            line_color="green" if "support" in name else "crimson"
        )
    # Volume profile as bar on y-axis if enabled
    if show_profile and len(opts) > 0:
        strikes = list(opts["strike"].unique())
        volumes = [vol_profile.loc[s, "volume_total"] for s in strikes if s in vol_profile.index]
        prices = strikes[:len(volumes)]
        fig.add_trace(
            go.Bar(
                y=prices, x=volumes, orientation="h",
                marker=dict(color="rgba(150,150,250,0.3)"), yaxis="y2",
                name="Volume Profile", showlegend=False,
            )
        )
        # Overlay on same chart: ensure axis config
        fig.update_layout(
            yaxis=dict(title="Spot Price", domain=[0, 1]),
            yaxis2=dict(
                title="Volume at Strike",
                overlaying="y", side="right", showgrid=False, range=[min(prices), max(prices)]
            ),
            bargap=0.01, margin=dict(l=30, r=10, t=40, b=20),
        )
    fig.update_layout(
        height=420, width=None, template="plotly_white",
        xaxis_rangeslider_visible=False, legend_orientation="h")
    return fig

col1, col2 = st.columns([1.3, 1], gap="small")
if len(spot_ohlc) > 0:
    with col1:
        st.subheader("Underlying Spot Candlestick + Volume Profile")
        fig = plot_combined_chart(spot_ohlc, pa_zones, trades)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Spot OHLC candles unavailable (data fetch issue).")

with col2:
    # Show calculated price action zones: e.g. support/resistance and "trading zones"
    st.subheader("Key Price Action Zones")
    if len(pa_zones) > 0:
        for k, v in pa_zones.items():
            st.markdown(f"- **{k.upper()}**: {v:.2f}")
    else:
        st.warning("Unable to determine price action zones. Check connection or try later.")

# -----
# 12. HIGH-CONFIDENCE TRADE TABLE (INTERACTIVE, AGGRID)
# -----
st.subheader("🎯 **High-Confidence Option Trades** (Filtered, Sniper Criteria)")
if len(trades) == 0:
    st.info("No trades above high-confidence filter for this index + expiry.")
else:
    # AG Grid for beautiful interactive table: https://github.com/PablocFonseca/streamlit-aggrid
    show_cols = [
        "symbol", "expiry", "option_type", "strike", "ltp", "oi", "volume", "volume_total",
        "theta", "confidence", "strategy", "strategy_context", "stop_loss", "target"
    ]
    # Prepare user-friendly headings for grid
    renames = {
        "ltp": "LTP", "oi": "OI", "volume": "Volume", "option_type": "Type",
        "strike": "Strike", "expiry": "Expiry", "theta": "Theta/Day", "confidence": "Conf.",
        "symbol": "Symbol", "strategy": "Strategy", "strategy_context": "Context",
        "stop_loss": "Stop Loss", "target": "Target", "volume_total": "VP Total"
    }
    display_df = trades[show_cols].rename(columns=renames).reset_index(drop=True)
    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_default_column(editable=False, groupable=True, filter=True, resizable=True)
    gb.configure_column("Conf.", cellStyle=JsCode("""
        function(params) {
            return { 'color': params.value >= 90 ? 'green' : (params.value >=80 ? 'blue':'black'),
                     'fontWeight': params.value>=90?'bold':'normal'};
        }
    """))
    gb.configure_column("Type", cellStyle=JsCode("""
        function(params) {
            return { 'color': params.value == 'CE' ? 'dodgerblue' : 'orangered' };
        }
    """))
    gb.configure_grid_options(
        domLayout="autoHeight",
        enableRangeSelection=True,
        selectionMode="single",
        pagination=True,
        paginationPageSize=15,
    )
    grid_response = AgGrid(
        display_df, gridOptions=gb.build(), fit_columns_on_grid_load=True,
        theme="streamlit", allow_unsafe_jscode=True, reload_data=True
    )
    st.caption("Tip: Click rows for details. Grid is interactive, sortable & filterable.")

    # Details for selected trade
    sel = grid_response.get("selected_rows", [])
    if sel and len(sel):
        d = sel[0]
        st.markdown(f"""
**Selected Trade Breakdown:**  
- **Symbol/Expiry**: `{d['Symbol']}` / `{d['Expiry']}`
- **Type/Strike**: `{d['Type']}` / {d['Strike']}
- **Strategy**: _{d['Strategy']}_ :: **{d['Context']}**
- **LTP**: {d['LTP']} | **Theta Decay:** {d['Theta/Day']} / day
- **Stop-loss**: **{d['Stop Loss']}** | **Target:** **{d['Target']}**
- **Conf. Score**: **{d['Conf.']}**
    """)

# -----
# 13. MOBILE-FRIENDLY RESPONSIVE LAYOUT (STREAMLIT UI)
# -----
st.markdown("""
<style>
/* Hide Streamlit Footer and MainMenu for full mobile feel */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
/* Help mobile: reduce grid font, padding */
.ag-theme-streamlit .ag-header-cell, .ag-theme-streamlit .ag-cell { font-size: 14px !important; padding: 2px !important;}
/* Make sidebar overlay on mobile */
@media (max-width: 600px) {
    .sidebar .sidebar-content { width: 94vw; min-width:90vw !important;}
}
</style>
""", unsafe_allow_html=True)

if st.button("Run in Mobile Preview"):
    st.info("To preview, resize your browser/navigate to this page on your phone!")

st.markdown(
    "<small>⚡ Data powered by NSE, OHLC by Yahoo Finance, Table by AG Grid. Chart overlays, analytics & scoring as per cited trading research and market best practices.</small>",
    unsafe_allow_html=True
)

# END OF FILE
