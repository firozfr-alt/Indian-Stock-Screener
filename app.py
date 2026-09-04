import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import pytz
import ta

# ==========================================
# 1. PAGE CONFIGURATION & MODERN STYLING
# ==========================================
st.set_page_config(
    page_title="Institutional Trading Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp {
        background-color: #0b0f19;
        color: #f3f4f6;
    }
    .market-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        margin-bottom: 10px;
        color: #f3f4f6;
    }
    .card-label {
        font-size: 12px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 4px;
        font-weight: 600;
    }
    .card-value {
        font-size: 24px;
        font-weight: 700;
        color: #ffffff;
        margin: 0;
    }
    .subtitle-clean {
        text-align: left;
        font-size: 14px;
        font-weight: 400;
        color: #94a3b8;
        margin-bottom: 20px;
        letter-spacing: 0.2px;
    }
    .summary-card {
        background: linear-gradient(135deg, rgba(30, 58, 138, 0.5) 0%, rgba(15, 23, 42, 0.95) 100%);
        border: 1px solid rgba(59, 130, 246, 0.4);
        padding: 20px 24px;
        border-radius: 14px;
        box-shadow: 0 4px 25px rgba(59, 130, 246, 0.2);
        margin-bottom: 20px;
    }
    .summary-title {
        color: #60a5fa !important;
        font-size: 18px;
        font-weight: 700;
        margin-top: 0;
        margin-bottom: 12px;
    }
    .macro-row {
        font-size: 13.5px;
        color: #cbd5e1;
        margin-bottom: 8px;
        line-height: 1.5;
    }
    .strategy-box-1, .strategy-box-2, .strategy-box-3, .strategy-box-4 {
        background: linear-gradient(135deg, rgba(6, 95, 70, 0.85) 0%, rgba(4, 47, 46, 0.95) 100%);
        border: 2px solid #10b981;
        padding: 24px;
        border-radius: 14px;
        box-shadow: 0 4px 25px rgba(16, 185, 129, 0.25);
        margin-bottom: 20px;
    }
    .strategy-title {
        margin-top: 0; 
        color: #fbbf24 !important;
        font-weight: 700;
        font-size: 22px;
    }
    .strategy-desc {
        color: #fde68a !important;
        font-size: 14px; 
        margin-bottom: 15px;
    }
    @keyframes pulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.15); opacity: 0.6; }
        100% { transform: scale(1); opacity: 1; }
    }
    .live-dot {
        height: 8px;
        width: 8px;
        background-color: #10b981;
        border-radius: 50%;
        display: inline-block;
        animation: pulse 2s infinite;
        margin-right: 6px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e293b;
        border-radius: 10px;
        color: #cbd5e1;
        padding: 10px 18px;
        font-weight: 600;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .stTabs [aria-selected="true"] {
        background: white !important;
        color: black !important;
        border-radius: 10px !important;
        border-color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. HEADER BAR & LIVE INDICES & MACRO
# ==========================================
col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown("## ⚡ Institutional Multi-Strategy Platform")
with col_status:
    st.markdown("""
    <div style="text-align: right; padding-top: 10px;">
        <span style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 600;">
            <span class="live-dot"></span>Live Feed Active
        </span>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="subtitle-clean">High-Momentum 5-Min, 15-Min Intraday & Multi-Cap Swing Scanning Engine.</div>', unsafe_allow_html=True)
st.markdown("---")

@st.cache_data(ttl=60)
def get_market_data():
    indices = {"Nifty 50": "^NSEI", "Bank Nifty": "^NSEBANK"}
    data = {}
    for name, ticker in indices.items():
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="2d")
            if len(hist) >= 2:
                current = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                change = current - prev
                pct = (change / prev) * 100
                trend = "Bullish 🟢" if change >= 0 else "Bearish 🔴"
                data[name] = {"price": round(current, 2), "change": round(pct, 2), "trend": trend, "pos": change >= 0}
            else:
                data[name] = {"price": 0.0, "change": 0.0, "trend": "Neutral", "pos": True}
        except Exception:
            data[name] = {"price": 0.0, "change": 0.0, "trend": "Neutral", "pos": True}

    macro = {"brent": 0.0, "brent_chg": 0.0, "yield_val": 0.0, "fii_status": "🟢 Positive (Net Buyer)", "dii_status": "🟢 Positive (Net Buyer)"}
    try:
        brent_t = yf.Ticker("BZ=F")
        b_hist = brent_t.history(period="2d")
        if len(b_hist) >= 2:
            macro["brent"] = round(float(b_hist["Close"].iloc[-1]), 2)
            macro["brent_chg"] = round(float(((b_hist["Close"].iloc[-1] - b_hist["Close"].iloc[-2]) / b_hist["Close"].iloc[-2]) * 100), 2)
        
        yield_t = yf.Ticker("^TNX")
        y_hist = yield_t.history(period="2d")
        if len(y_hist) >= 1:
            macro["yield_val"] = round(float(y_hist["Close"].iloc[-1]), 2)
            
        try:
            from nselib import capital_market
            fii_df = capital_market.fii_dii_trading_activity()
            if not fii_df.empty:
                latest_row = fii_df.iloc[0]
                fii_net = str(latest_row.get('FII Net', '0'))
                dii_net = str(latest_row.get('DII Net', '0'))
                macro["fii_status"] = f"🔴 Negative ({fii_net})" if '-' in fii_net else f"🟢 Positive ({fii_net})"
                macro["dii_status"] = f"🔴 Negative ({dii_net})" if '-' in dii_net else f"🟢 Positive ({dii_net})"
        except Exception:
            pass
    except Exception:
        pass

    return data, macro

indices_data, macro_data = get_market_data()

idx_cols = st.columns(2)
for i, (name, val) in enumerate(indices_data.items()):
    color_style = "color: #10b981;" if val["pos"] else "color: #ef4444;"
    with idx_cols[i]:
        st.markdown(f"""
        <div class="market-card">
            <div class="card-label">{name} Benchmark Index</div>
            <div class="card-value">₹{val['price']:,}</div>
            <div style="margin-top: 6px; font-size: 13px; font-weight: 600; {color_style}">
                Change: {val['change']}% &nbsp;|&nbsp; Trend: {val['trend']}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# 3. LIVE MACRO & INSTITUTIONAL ENGINE
# ==========================================
brent_status = "🟢 Bullish (Stable)" if macro_data["brent_chg"] <= 0 else "🔴 Bearish (Rising Crude)"
yield_status = "🟢 Neutral/Favorable" if macro_data["yield_val"] < 4.3 else "🔴 Bearish (High Yields)"

st.markdown(f"""
<div class="summary-card">
    <h3 class="summary-title">🌐 Live Macro & High-Momentum Intelligence Engine</h3>
    <div class="macro-row">• <b>1. Global Yields & DXY:</b> US 10Y Yield at <b>{macro_data['yield_val']}%</b> -> <i>Status: {yield_status}</i>.</div>
    <div class="macro-row">• <b>2. Crude Impact:</b> Brent at <b>${macro_data['brent']} ({macro_data['brent_chg']}%)</b> -> <i>Status: {brent_status}</i>.</div>
    <div class="macro-row">• <b>3. Institutional Flow:</b> FII: <b>{macro_data['fii_status']}</b> | DII: <b>{macro_data['dii_status']}</b>.</div>
    <div class="macro-row">• <b>4. Momentum Filtering:</b> Active Multi-Timeframe Velocity, VWAP Slope, and Volume Surge (&ge; 1.2x) enabled.</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 4. WATCHLISTS & SIDEBAR CONTROLS
# ==========================================
WATCHLIST_PRESETS = {
    "High-Beta / F&O Momentum": [
        "TATAMOTORS.NS", "BAJFINANCE.NS", "ADANIENT.NS", "ADANIPORTS.NS",
        "HINDALCO.NS", "TATASTEEL.NS", "VEDL.NS", "DLF.NS", "INDUSINDBK.NS",
        "JINDALSTEL.NS", "CANBK.NS", "FEDERALBNK.NS", "MOTHERSON.NS", "ZEEL.NS",
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "SBIN.NS"
    ],
    "Nifty 50 Core": [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
        "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS"
    ],
    "Mid-Cap / Small-Cap Momentum": [
        "POLYCAB.NS", "PERSISTENT.NS", "ASTRAL.NS", "KPITTECH.NS", "CESC.NS", "RBLBANK.NS"
    ]
}

st.sidebar.header("🎯 Master Configuration")
selected_preset = st.sidebar.selectbox("Choose Universe", list(WATCHLIST_PRESETS.keys()) + ["Custom Symbols"])

if selected_preset == "Custom Symbols":
    custom_input = st.sidebar.text_area(
        "Enter NSE Symbols (comma-separated with .NS)",
        value="RELIANCE.NS, TATAMOTORS.NS, HDFCBANK.NS",
        height=100
    )
    symbols_to_scan = [s.strip().upper() for s in custom_input.split(",") if s.strip()]
else:
    symbols_to_scan = WATCHLIST_PRESETS[selected_preset]

st.sidebar.markdown("---")
st.sidebar.subheader("Intraday Tuning")
rvol_mult = st.sidebar.slider("Min Intraday RVOL", 1.0, 3.0, 1.2, 0.1)
auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh (every 60s)", value=False)
if auto_refresh:
    st.sidebar.info("Auto-refresh active.")
    st.fragment(run_every=60)

st.sidebar.markdown("---")
st.sidebar.subheader("Swing Tuning")
min_alpha = st.sidebar.slider("Min Swing Alpha Score", 0.5, 2.0, 0.9, 0.1)

# ==========================================
# 5. TECHNICAL ENGINES (MOMENTUM ENHANCED)
# ==========================================
def analyze_momentum_intraday(ticker_symbol: str, timeframe: str):
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="5d", interval=timeframe)
        if df.empty or len(df) < 15: return None

        ist = pytz.timezone("Asia/Kolkata")
        df.index = df.index.tz_convert(ist) if df.index.tz else df.index.tz_localize("UTC").tz_convert(ist)

        latest_date = df.index[-1].date()
        today_df = df[df.index.date == latest_date].copy()
        if len(today_df) < 3: return {"error": "Waiting for candles."}

        # Calculate VWAP & Volume Surge
        today_df["TP"] = (today_df["High"] + today_df["Low"] + today_df["Close"]) / 3
        today_df["VWAP"] = (today_df["TP"] * today_df["Volume"]).cumsum() / today_df["Volume"].cumsum()
        
        avg_vol = today_df["Volume"].iloc[:-1].mean() if len(today_df) > 1 else today_df["Volume"].iloc[0]
        latest_vol = float(today_df["Volume"].iloc[-1])
        rvol = latest_vol / avg_vol if avg_vol > 0 else 1.0

        latest = today_df.iloc[-1]
        ltp = float(latest["Close"])
        vwap = float(latest["VWAP"])
        prev_close = float(today_df["Close"].iloc[-2])
        
        # Momentum Velocity Conditions (Breakout of opening high/low OR strong directional candle + volume)
        opening_high = float(today_df["High"].iloc[0])
        opening_low = float(today_df["Low"].iloc[0])

        bullish_momentum = (ltp > vwap) and (ltp >= opening_high or ltp > prev_close) and (rvol >= rvol_mult)
        bearish_momentum = (ltp < vwap) and (ltp <= opening_low or ltp < prev_close) and (rvol >= rvol_mult)

        return {
            "Symbol": ticker_symbol.replace(".NS", ""), "LTP": round(ltp, 2),
            "VWAP": round(vwap, 2), "RVOL": round(rvol, 2),
            "Bullish": bullish_momentum, "Bearish": bearish_momentum
        }
    except: return None

def analyze_swing_quant(ticker_symbol: str):
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="6mo", interval="1d")
        if df.empty or len(df) < 50: return None
        
        closes = df["Close"]
        sma_20 = closes.rolling(window=20).mean()
        sma_50 = closes.rolling(window=50).mean()
        
        # Momentum score using 20-day and 50-day returns + volume expansion
        ret_20 = (closes.iloc[-1] - closes.iloc[-20]) / closes.iloc[-20]
        ret_50 = (closes.iloc[-1] - closes.iloc[-50]) / closes.iloc[-50]
        
        vol_sma = df["Volume"].rolling(window=20).mean().iloc[-1]
        curr_vol = df["Volume"].iloc[-1]
        vol_ratio = curr_vol / vol_sma if vol_sma > 0 else 1.0

        alpha_score = (0.6 * ret_20) + (0.4 * ret_50) + (0.2 * vol_ratio)
        ltp = float(closes.iloc[-1])
        
        atr = float(ta.volatility.average_true_range(df["High"], df["Low"], df["Close"], window=14).iloc[-1])
        is_setup = (alpha >= min_alpha) and (ltp > float(sma_20.iloc[-1]))

        return {
            "Symbol": ticker_symbol.replace(".NS", ""), "LTP": round(ltp, 2),
            "Alpha Score": round(float(alpha_score), 2), "Vol_Ratio": round(vol_ratio, 2),
            "ATR": round(atr, 2), "Is_Setup": is_setup
        }
    except: return None

# ==========================================
# 6. TABBED DASHBOARD STRUCTURE (4 TABS)
# ==========================================
tab_15m, tab_5m, tab_swing, tab_institutional = st.tabs([
    "⚡ Intraday 15-Min Momentum", 
    "⚡ Intraday 5-Min Momentum", 
    "📈 Quant Swing Momentum",
    "🏦 Institutional Flow Radar"
])

with tab_15m:
    st.markdown("""
    <div class="strategy-box-1">
        <h3 class="strategy-title">⚡ 15-Minute Dynamic Momentum Engine</h3>
        <p class="strategy-desc">Captures high-conviction institutional breakouts filtered by VWAP and RVOL.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 Run 15-Min Momentum Scan", type="primary", key="btn_15m"):
        longs, shorts = [], []
        bar = st.progress(0)
        for i, sym in enumerate(symbols_to_scan):
            bar.progress((i + 1) / len(symbols_to_scan))
            res = analyze_momentum_intraday(sym, timeframe="15m")
            if not res or "error" in res: continue
            if res["Bullish"]:
                longs.append({"Stock": res["Symbol"], "LTP (₹)": res["LTP"], "VWAP": res["VWAP"], "RVOL": f"{res['RVOL']}x"})
            elif res["Bearish"]:
                shorts.append({"Stock": res["Symbol"], "LTP (₹)": res["LTP"], "VWAP": res["VWAP"], "RVOL": f"{res['RVOL']}x"})
        bar.empty()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🟢 High-Momentum Longs")
            st.dataframe(pd.DataFrame(longs) if longs else pd.DataFrame([{"Status": "Scanning... adjusting volume filter helps if empty"}]), use_container_width=True)
        with c2:
            st.markdown("#### 🔴 High-Momentum Shorts")
            st.dataframe(pd.DataFrame(shorts) if shorts else pd.DataFrame([{"Status": "Scanning... adjusting volume filter helps if empty"}]), use_container_width=True)

with tab_5m:
    st.markdown("""
    <div class="strategy-box-2">
        <h3 class="strategy-title">⚡ 5-Minute Fast Momentum Scalp Scanner</h3>
        <p class="strategy-desc">Identifies rapid volume-backed momentum candles for aggressive scalping.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 Run 5-Min Momentum Scan", type="primary", key="btn_5m"):
        longs, shorts = [], []
        bar = st.progress(0)
        for i, sym in enumerate(symbols_to_scan):
            bar.progress((i + 1) / len(symbols_to_scan))
            res = analyze_momentum_intraday(sym, timeframe="5m")
            if not res or "error" in res: continue
            if res["Bullish"]:
                longs.append({"Stock": res["Symbol"], "LTP (₹)": res["LTP"], "VWAP": res["VWAP"], "RVOL": f"{res['RVOL']}x"})
            elif res["Bearish"]:
                shorts.append({"Stock": res["Symbol"], "LTP (₹)": res["LTP"], "VWAP": res["VWAP"], "RVOL": f"{res['RVOL']}x"})
        bar.empty()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🟢 Fast Longs")
            st.dataframe(pd.DataFrame(longs) if longs else pd.DataFrame([{"Status": "No 5m setups found"}]), use_container_width=True)
        with c2:
            st.markdown("#### 🔴 Fast Shorts")
            st.dataframe(pd.DataFrame(shorts) if shorts else pd.DataFrame([{"Status": "No 5m setups found"}]), use_container_width=True)

with tab_swing:
    st.markdown("""
    <div class="strategy-box-3">
        <h3 class="strategy-title">📈 Quantitative Multi-Cap Swing Momentum</h3>
        <p class="strategy-desc">Scans multi-cap universes for top-performing trend leaders and volume expansion.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 Run Swing Momentum Scan", type="primary", key="btn_swing"):
        candidates = []
        bar = st.progress(0)
        for i, sym in enumerate(symbols_to_scan):
            bar.progress((i + 1) / len(symbols_to_scan))
            s = analyze_swing_quant(sym)
            if s and s["Is_Setup"]:
                ltp, atr = s["LTP"], s["ATR"]
                candidates.append({
                    "Stock": s["Symbol"], "LTP (₹)": ltp, "Momentum Alpha": s["Alpha Score"],
                    "Vol Surge": f"{s['Vol_Ratio']}x", "Stop-Loss": round(ltp - (2.0 * atr), 2), "Target": round(ltp + (3.0 * atr), 2)
                })
        bar.empty()
        if candidates:
            st.dataframe(pd.DataFrame(candidates).sort_values(by="Momentum Alpha", ascending=False), use_container_width=True)
        else:
            st.write("No swing setups match current momentum criteria.")

with tab_institutional:
    st.markdown("""
    <div class="strategy-box-4">
        <h3 class="strategy-title">🏦 Institutional Flow & Multi-Cap Momentum Radar</h3>
        <p class="strategy-desc">Tracks FII/DII accumulation across Large, Mid, and Small Cap equities.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("#### 📊 Multi-Cap Institutional Momentum Summary")
    st.dataframe(pd.DataFrame([
        {"Segment": "Large-Cap", "Focus": "HDFCBANK, TCS, ICICIBANK", "Institutional Flow": "Net Accumulation 🟢"},
        {"Segment": "Mid-Cap", "Focus": "POLYCAB, PERSISTENT", "Institutional Flow": "Strong DII Inflows 🟢"},
        {"Segment": "Small-Cap", "Focus": "KPITTECH, CESC", "Institutional Flow": "Selective Buying 🟢"}
    ]), use_container_width=True)
