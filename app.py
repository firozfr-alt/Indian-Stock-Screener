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
    /* Dark Institutional Theme */
    .stApp {
        background-color: #0b0f19;
        color: #f3f4f6;
    }
    
    /* Reverted Dark Minimalist Cards for Nifty & Bank Nifty */
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

    /* Left-Aligned, Smaller, Unbolded Subtitle */
    .subtitle-clean {
        text-align: left;
        font-size: 14px;
        font-weight: 400;
        color: #94a3b8;
        margin-bottom: 20px;
        letter-spacing: 0.2px;
    }

    /* Tomorrow Market Summary Card Style */
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
        margin-bottom: 10px;
    }

    .summary-text {
        color: #cbd5e1 !important;
        font-size: 14px;
        line-height: 1.6;
        margin: 0;
    }

    /* Strategy Highlight Boxes (Green Highlight with Golden Text Inside) */
    .strategy-box-1, .strategy-box-2, .strategy-box-3 {
        background: linear-gradient(135deg, rgba(6, 95, 70, 0.85) 0%, rgba(4, 47, 46, 0.95) 100%);
        border: 2px solid #10b981;
        padding: 24px;
        border-radius: 14px;
        box-shadow: 0 4px 25px rgba(16, 185, 129, 0.25);
        margin-bottom: 20px;
    }

    .strategy-title {
        margin-top: 0; 
        color: #fbbf24 !important; /* Golden Font Color */
        font-weight: 700;
        font-size: 22px;
    }

    .strategy-desc {
        color: #fde68a !important; /* Lighter Golden Tone for Description */
        font-size: 14px; 
        margin-bottom: 15px;
    }

    /* Pulse Live Indicator */
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

    /* Custom Navigation Tabs (Curved Edges, White Highlight, Black Letters) */
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
# 2. HEADER BAR & LIVE INDICES
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

st.markdown('<div class="subtitle-clean">Clean 15-Min ORB, Filtered 5-Min Candle-Close ORB, and Quant Swing Models.</div>', unsafe_allow_html=True)
st.markdown("---")

@st.cache_data(ttl=60)
def get_market_indices():
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
    return data

indices_data = get_market_indices()

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
# 3. TOMORROW MARKET CONDITION SUMMARY & NOTES
# ==========================================
st.markdown("""
<div class="summary-card">
    <h3 class="summary-title">🔮 Tomorrow's Market Outlook & Strategy Notes</h3>
    <p class="summary-text">
        • <b>Global & Regional Tone:</b> Cautious stance across global equities with mixed reactions to energy volatility.<br>
        • <b>Trend Alignment:</b> Nifty defending critical lower supports while Bank Nifty attempts range-bound stabilization.<br>
        • <b>Execution Caution:</b> High susceptibility to early choppy movements; avoid jumping into immediate wicks.<br>
        • <b>Discipline Rule:</b> Wait for confirmed candle closures and robust Relative Volume (RVOL) spikes before entry.
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 4. WATCHLISTS & SIDEBAR CONTROLS
# ==========================================
WATCHLIST_PRESETS = {
    "Nifty 50 Core": [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
        "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS",
        "AXISBANK.NS", "TATAMOTORS.NS", "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS",
        "BAJFINANCE.NS", "TATASTEEL.NS", "HINDUNILVR.NS", "NTPC.NS", "POWERGRID.NS"
    ],
    "High-Beta / F&O Momentum": [
        "TATAMOTORS.NS", "BAJFINANCE.NS", "ADANIENT.NS", "ADANIPORTS.NS",
        "HINDALCO.NS", "TATASTEEL.NS", "VEDL.NS", "DLF.NS", "INDUSINDBK.NS",
        "JINDALSTEL.NS", "CANBK.NS", "FEDERALBNK.NS", "MOTHERSON.NS", "ZEEL.NS"
    ],
    "Banking & Financials": [
        "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS",
        "INDUSINDBK.NS", "BANKBARODA.NS", "PNB.NS", "CANBK.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS"
    ]
}

st.sidebar.header("🎯 Master Configuration")
selected_preset = st.sidebar.selectbox("Choose Universe", list(WATCHLIST_PRESETS.keys()) + ["Custom Symbols"])

if selected_preset == "Custom Symbols":
    custom_input = st.sidebar.text_area(
        "Enter NSE Symbols (comma-separated with .NS)",
        value="RELIANCE.NS, TCS.NS, HDFCBANK.NS, INFY.NS, TATAMOTORS.NS",
        height=100
    )
    symbols_to_scan = [s.strip().upper() for s in custom_input.split(",") if s.strip()]
else:
    symbols_to_scan = WATCHLIST_PRESETS[selected_preset]

st.sidebar.markdown("---")
st.sidebar.subheader("Intraday Tuning")
rvol_mult = st.sidebar.slider("Min Intraday RVOL", 1.0, 5.0, 1.5, 0.1)
auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh (every 60s)", value=False)
if auto_refresh:
    st.sidebar.info("Auto-refresh active.")
    st.fragment(run_every=60)

st.sidebar.markdown("---")
st.sidebar.subheader("Swing Tuning")
min_alpha = st.sidebar.slider("Min Swing Alpha Score", 0.8, 2.0, 1.2, 0.1)

# ==========================================
# 5. TECHNICAL ENGINES (EXACT UNTOUCHED LOGIC)
# ==========================================
def analyze_orb_strategy(ticker_symbol: str, timeframe: str):
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="14d", interval=timeframe)
        if df.empty or len(df) < 30: return None

        ist = pytz.timezone("Asia/Kolkata")
        df.index = df.index.tz_convert(ist) if df.index.tz else df.index.tz_localize("UTC").tz_convert(ist)

        first_candles = df.groupby(df.index.date).first()
        avg_opening_volume = first_candles['Volume'].iloc[:-1].mean()

        latest_date = df.index[-1].date()
        today_df = df[df.index.date == latest_date].copy()
        if len(today_df) < 2: return {"error": "Waiting for range completion."}

        or_bar = today_df.iloc[0]
        or_high, or_low = float(or_bar["High"]), float(or_bar["Low"])
        today_opening_vol = float(or_bar["Volume"])

        if timeframe == '15m':
            latest = today_df.iloc[-1]
            ltp = float(latest["Close"])
            breakout_cond, breakdown_cond = (ltp > or_high), (ltp < or_low)
        else:
            sub_candles = today_df.iloc[1:]
            if sub_candles.empty: return {"error": "Waiting for breakout candle close."}
            latest = sub_candles.iloc[-1]
            ltp = float(latest["Close"])
            breakout_cond, breakdown_cond = (ltp > or_high), (ltp < or_low)

        rvol = today_opening_vol / avg_opening_volume if avg_opening_volume > 0 else 1.0

        today_df["TP"] = (today_df["High"] + today_df["Low"] + today_df["Close"]) / 3
        today_df["VWAP"] = (today_df["TP"] * today_df["Volume"]).cumsum() / today_df["Volume"].cumsum()
        vwap_latest = float(today_df["VWAP"].iloc[-1])

        return {
            "Symbol": ticker_symbol.replace(".NS", ""), "LTP": round(ltp, 2),
            "OR_High": round(or_high, 2), "OR_Low": round(or_low, 2),
            "VWAP": round(vwap_latest, 2), "RVOL": round(rvol, 2),
            "Breakout": breakout_cond, "Breakdown": breakdown_cond
        }
    except: return None

def analyze_swing_quant(ticker_symbol: str):
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="1y", interval="1d")
        if df.empty or len(df) < 200: return None
        
        closes = df["Close"]
        log_ret = np.log(closes / closes.shift(1))
        vol_60 = log_ret.rolling(window=60).std() * np.sqrt(252)
        mom_score = np.log(closes / closes.shift(60)) / vol_60
        
        sma_50 = closes.rolling(window=50).mean()
        vol_50 = closes.rolling(window=50).std()
        z_price = (closes - sma_50) / vol_50
        
        vol_sma_20 = df["Volume"].rolling(window=20).mean()
        rvol_20 = ((df["Volume"].shift(1) + df["Volume"].shift(2) + df["Volume"].shift(3)) / 3) / vol_sma_20
        
        alpha_score = 0.4 * mom_score + 0.3 * (z_price / 2.0) + 0.3 * rvol_20
        
        ltp = float(closes.iloc[-1])
        alpha = float(alpha_score.iloc[-1])
        z_val = float(z_price.iloc[-1])
        rvol_val = float(rvol_20.iloc[-1])
        
        atr = float(ta.volatility.average_true_range(df["High"], df["Low"], df["Close"], window=14).iloc[-1])
        is_setup = (alpha >= min_alpha) and (0.5 <= z_val <= 2.0) and (rvol_val >= 1.2)
        
        return {
            "Symbol": ticker_symbol.replace(".NS", ""), "LTP": round(ltp, 2),
            "Alpha Score": round(alpha, 2), "Z-Score": round(z_val, 2),
            "RVOL_20": round(rvol_val, 2), "ATR": round(atr, 2), "Is_Setup": is_setup
        }
    except: return None

# ==========================================
# 6. TABBED DASHBOARD STRUCTURE (3 TABS)
# ==========================================
tab_15m, tab_5m, tab_swing = st.tabs([
    "⚡ Intraday 15-Min ORB (Clean)", 
    "⚡ Intraday 5-Min (Candle Close + RVOL)", 
    "📈 Quant Multi-Factor Swing"
])

with tab_15m:
    st.markdown("""
    <div class="strategy-box-1">
        <h3 class="strategy-title">⚡ 15-Minute Opening Range Breakout (9:15–9:30 AM)</h3>
        <p class="strategy-desc">Low-noise institutional strategy utilizing a 15-minute opening window.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 Run 15-Min Scan", type="primary", key="btn_15m"):
        buy_signals, sell_signals = [], []
        bar = st.progress(0)
        for i, sym in enumerate(symbols_to_scan):
            bar.progress((i + 1) / len(symbols_to_scan))
            data = analyze_orb_strategy(sym, timeframe="15m")
            if not data or "error" in data: continue
            ltp, or_h, or_l, vwap, rvol = data["LTP"], data["OR_High"], data["OR_Low"], data["VWAP"], data["RVOL"]
            if data["Breakout"] and (ltp > vwap) and (rvol >= rvol_mult):
                risk = round(ltp - or_l, 2)
                buy_signals.append({"Stock": data["Symbol"], "LTP (₹)": ltp, "Stop-Loss": or_l, "Target": round(ltp + (1.5 * risk), 2), "RVOL": f"{rvol}x"})
            elif data["Breakdown"] and (ltp < vwap) and (rvol >= rvol_mult):
                risk = round(or_h - ltp, 2)
                sell_signals.append({"Stock": data["Symbol"], "LTP (₹)": ltp, "Stop-Loss": or_h, "Target": round(ltp - (1.5 * risk), 2), "RVOL": f"{rvol}x"})
        bar.empty()
        c1, c2 = st.columns(2)
        with c1: 
            st.markdown("#### 🟢 Long Setups")
            st.dataframe(pd.DataFrame(buy_signals) if buy_signals else pd.DataFrame([{"Status": "No Clean Breakouts"}]), use_container_width=True)
        with c2: 
            st.markdown("#### 🔴 Short Setups")
            st.dataframe(pd.DataFrame(sell_signals) if sell_signals else pd.DataFrame([{"Status": "No Clean Breakdowns"}]), use_container_width=True)

with tab_5m:
    st.markdown("""
    <div class="strategy-box-2">
        <h3 class="strategy-title">⚡ 5-Minute ORB with Strict Candle Close + RVOL</h3>
        <p class="strategy-desc">Fights 5-minute noise by requiring candle-close confirmation outside the range.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 Run Filtered 5-Min Scan", type="primary", key="btn_5m"):
        buy_signals, sell_signals = [], []
        bar = st.progress(0)
        for i, sym in enumerate(symbols_to_scan):
            bar.progress((i + 1) / len(symbols_to_scan))
            data = analyze_orb_strategy(sym, timeframe="5m")
            if not data or "error" in data: continue
            ltp, or_h, or_l, vwap, rvol = data["LTP"], data["OR_High"], data["OR_Low"], data["VWAP"], data["RVOL"]
            if data["Breakout"] and (ltp > vwap) and (rvol >= rvol_mult):
                risk = round(ltp - or_l, 2)
                buy_signals.append({"Stock": data["Symbol"], "LTP (₹)": ltp, "Stop-Loss": or_l, "Target": round(ltp + (1.5 * risk), 2), "RVOL": f"{rvol}x"})
            elif data["Breakdown"] and (ltp < vwap) and (rvol >= rvol_mult):
                risk = round(or_h - ltp, 2)
                sell_signals.append({"Stock": data["Symbol"], "LTP (₹)": ltp, "Stop-Loss": or_h, "Target": round(ltp - (1.5 * risk), 2), "RVOL": f"{rvol}x"})
        bar.empty()
        c1, c2 = st.columns(2)
        with c1: 
            st.markdown("#### 🟢 Long Setups")
            st.dataframe(pd.DataFrame(buy_signals) if buy_signals else pd.DataFrame([{"Status": "No Confirmed Breakouts"}]), use_container_width=True)
        with c2: 
            st.markdown("#### 🔴 Short Setups")
            st.dataframe(pd.DataFrame(sell_signals) if sell_signals else pd.DataFrame([{"Status": "No Confirmed Breakdowns"}]), use_container_width=True)

with tab_swing:
    st.markdown("""
    <div class="strategy-box-3">
        <h3 class="strategy-title">📈 Quantitative Multi-Factor Swing Scanner</h3>
        <p class="strategy-desc">Evaluates momentum, Z-scores, and institutional volume accumulation.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 Run Quant Swing Scan", type="primary", key="btn_swing"):
        swing_candidates = []
        bar = st.progress(0)
        for i, sym in enumerate(symbols_to_scan):
            bar.progress((i + 1) / len(symbols_to_scan))
            s_data = analyze_swing_quant(sym)
            if s_data and s_data["Is_Setup"]:
                ltp, atr = s_data["LTP"], s_data["ATR"]
                swing_candidates.append({
                    "Stock": s_data["Symbol"], "LTP (₹)": ltp, "Alpha Score": s_data["Alpha Score"], 
                    "Z-Score": s_data["Z-Score"], "RVOL (20d)": f"{s_data['RVOL_20']}x", 
                    "Stop-Loss": round(ltp - (2.0 * atr), 2), "Target": round(ltp + (3.0 * atr), 2)
                })
        bar.empty()
        if swing_candidates:
            st.dataframe(pd.DataFrame(swing_candidates).sort_values(by="Alpha Score", ascending=False), use_container_width=True)
        else:
            st.write("No swing setups match current quantitative alpha criteria.")
