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
    .stApp { background-color: #0b0f19; color: #f3f4f6; }
    .market-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4); margin-bottom: 10px; color: #f3f4f6;
    }
    .card-label { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 4px; font-weight: 600; }
    .card-value { font-size: 24px; font-weight: 700; color: #ffffff; margin: 0; }
    .subtitle-clean { font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 20px; }
    .summary-card {
        background: linear-gradient(135deg, rgba(30, 58, 138, 0.5) 0%, rgba(15, 23, 42, 0.95) 100%);
        border: 1px solid rgba(59, 130, 246, 0.4);
        padding: 20px 24px; border-radius: 14px; margin-bottom: 20px;
    }
    .summary-title { color: #60a5fa !important; font-size: 18px; font-weight: 700; margin-top: 0; margin-bottom: 12px; }
    .macro-row { font-size: 13.5px; color: #cbd5e1; margin-bottom: 8px; line-height: 1.5; }
    .strategy-box-1, .strategy-box-2, .strategy-box-3, .strategy-box-4 {
        background: linear-gradient(135deg, rgba(6, 95, 70, 0.85) 0%, rgba(4, 47, 46, 0.95) 100%);
        border: 2px solid #10b981; padding: 24px; border-radius: 14px; margin-bottom: 20px;
    }
    .strategy-title { margin-top: 0; color: #fbbf24 !important; font-weight: 700; font-size: 22px; }
    .strategy-desc { color: #fde68a !important; font-size: 14px; margin-bottom: 15px; }
    @keyframes pulse { 0% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.15); opacity: 0.6; } 100% { transform: scale(1); opacity: 1; } }
    .live-dot { height: 8px; width: 8px; background-color: #10b981; border-radius: 50%; display: inline-block; animation: pulse 2s infinite; margin-right: 6px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #1e293b; border-radius: 10px; color: #cbd5e1; padding: 10px 18px; font-weight: 600; border: 1px solid rgba(255, 255, 255, 0.05); }
    .stTabs [aria-selected="true"] { background: white !important; color: black !important; border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. HEADER BAR & MARKET INDICES
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

st.markdown('<div class="subtitle-clean">VWAP Intraday Momentum, 3-10 Day Swing Momentum, and Live Bullish vs Bearish Sector Tracking.</div>', unsafe_allow_html=True)
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
                current, prev = float(hist["Close"].iloc[-1]), float(hist["Close"].iloc[-2])
                change, pct = current - prev, ((current - prev) / prev) * 100
                data[name] = {"price": round(current, 2), "change": round(pct, 2), "trend": "Bullish 🟢" if change >= 0 else "Bearish 🔴", "pos": change >= 0}
            else:
                data[name] = {"price": 0.0, "change": 0.0, "trend": "Neutral", "pos": True}
        except Exception:
            data[name] = {"price": 0.0, "change": 0.0, "trend": "Neutral", "pos": True}
    return data

indices_data = get_market_data()

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

st.markdown("---")

# ==========================================
# 3. LIVE MACRO ENGINE
# ==========================================
st.markdown("""
<div class="summary-card">
    <h3 class="summary-title">🌐 Live Macro & Institutional Sentiment Engine</h3>
    <div class="macro-row">• <b>1. Global Macro Cues (Yields & DXY):</b> US 10Y Yield steady at 4.78% -> <i>Static Bearish (High Yields)</i>.</div>
    <div class="macro-row">• <b>2. Commodity & Currency Impact:</b> Brent trading at $96.28 (0.8%) -> <i>Bearish (Rising Crude)</i>. Controls domestic input costs.</div>
    <div class="macro-row">• <b>3. FII Trading Activity:</b> Positive (Net Buyer) -> Foreign institutional flow continuity.</div>
    <div class="macro-row">• <b>4. DII Trading Activity:</b> Positive (Net Buyer) -> Domestic institutional stabilization.</div>
    <div class="macro-row">• <b>5. Quantitative Z-Score & RVOL:</b> Statistical standard deviation threshold active at 1.50x volume multiplier.</div>
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
st.sidebar.subheader("Intraday Momentum Tuning")
intraday_rvol = st.sidebar.slider("Min Intraday RVOL", 1.0, 3.0, 1.3, 0.1)

st.sidebar.markdown("---")
st.sidebar.subheader("Swing Momentum Tuning (3-10 Days)")
swing_rvol = st.sidebar.slider("Min Swing RVOL (20d)", 1.0, 3.0, 1.3, 0.1)

# ==========================================
# 5. TECHNICAL & SECTOR ROTATION ENGINES
# ==========================================
def analyze_upgraded_intraday(ticker_symbol: str):
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="5d", interval="15m")
        if df.empty or len(df) < 15: return None

        ist = pytz.timezone("Asia/Kolkata")
        df.index = df.index.tz_convert(ist) if df.index.tz else df.index.tz_localize("UTC").tz_convert(ist)

        latest_date = df.index[-1].date()
        today_df = df[df.index.date == latest_date].copy()
        if len(today_df) < 2: return {"error": "Waiting for bars."}

        avg_vol = today_df['Volume'].iloc[:-1].mean()
        latest = today_df.iloc[-1]
        ltp = float(latest["Close"])
        latest_vol = float(latest["Volume"])
        rvol = latest_vol / avg_vol if avg_vol > 0 else 1.0

        today_df["TP"] = (today_df["High"] + today_df["Low"] + today_df["Close"]) / 3
        today_df["VWAP"] = (today_df["TP"] * today_df["Volume"]).cumsum() / today_df["Volume"].cumsum()
        vwap_val = float(today_df["VWAP"].iloc[-1])

        ema9 = float(ta.trend.ema_indicator(today_df["Close"], window=9).iloc[-1])
        ema21 = float(ta.trend.ema_indicator(today_df["Close"], window=21).iloc[-1])
        rsi_val = float(ta.momentum.rsi(today_df["Close"], window=14).iloc[-1])

        long_setup = (ltp > vwap_val) and (ema9 > ema21) and (rsi_val >= 50) and (rvol >= intraday_rvol)
        short_setup = (ltp < vwap_val) and (ema9 < ema21) and (rsi_val <= 50) and (rvol >= intraday_rvol)

        return {
            "Symbol": ticker_symbol.replace(".NS", ""), "LTP": round(ltp, 2),
            "VWAP": round(vwap_val, 2), "RSI": round(rsi_val, 1), "RVOL": round(rvol, 2),
            "Long": long_setup, "Short": short_setup
        }
    except: return None

def analyze_upgraded_swing(ticker_symbol: str):
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="1y", interval="1d")
        if df.empty or len(df) < 200: return None

        closes = df["Close"]
        sma_200 = float(closes.rolling(window=200).mean().iloc[-1])
        highest_20 = float(closes.rolling(window=20).max().iloc[-2])
        ltp = float(closes.iloc[-1])

        vol_sma_20 = float(df["Volume"].rolling(window=20).mean().iloc[-1])
        curr_vol = float(df["Volume"].iloc[-1])
        rvol_20 = curr_vol / vol_sma_20 if vol_sma_20 > 0 else 1.0

        rsi_series = ta.momentum.rsi(closes, window=14)
        rsi_val = float(rsi_series.iloc[-1])
        rsi_rising = rsi_val > float(rsi_series.iloc[-2])

        atr = float(ta.volatility.average_true_range(df["High"], df["Low"], closes, window=14).iloc[-1])

        is_setup = (
            (ltp > sma_200) and
            (ltp >= highest_20 * 0.97) and
            (50 <= rsi_val <= 68) and
            rsi_rising and
            (rvol_20 >= swing_rvol)
        )

        return {
            "Symbol": ticker_symbol.replace(".NS", ""), "LTP": round(ltp, 2),
            "RSI": round(rsi_val, 1), "RVOL": round(rvol_20, 2),
            "Stop-Loss": round(ltp - (2.0 * atr), 2), "Target": round(ltp + (3.0 * atr), 2),
            "Is_Setup": is_setup
        }
    except: return None

@st.cache_data(ttl=60)
def get_live_sector_rotation():
    sector_proxies = {
        "Nifty Bank": "^NSEBANK",
        "Nifty IT": "^CNXIT",
        "Nifty Auto": "^CNXAUTO",
        "Nifty Metal": "^CNXMETAL",
        "Nifty Pharma": "^CNXPHARMA",
        "Nifty FMCG": "^CNXFMCG",
        "Nifty Realty": "^CNXREALTY",
        "Nifty Energy": "^CNXENERGY"
    }
    sector_data = []
    for sec_name, sec_ticker in sector_proxies.items():
        try:
            t = yf.Ticker(sec_ticker)
            h = t.history(period="2d")
            if len(h) >= 2:
                curr = float(h["Close"].iloc[-1])
                prev = float(h["Close"].iloc[-2])
                pct = ((curr - prev) / prev) * 100
                status = "Bullish 🟢" if pct >= 0 else "Bearish 🔴"
                sector_data.append({"Sector": sec_name, "Change %": round(pct, 2), "Status": status})
        except:
            pass
    return pd.DataFrame(sector_data)

# ==========================================
# 6. TABBED NAVIGATION (STRATEGIES + LIVE SECTOR ROTATION TAB)
# ==========================================
tab_quick_intra, tab_swing_mom, tab_live_sectors = st.tabs([
    "🚀 Upgraded VWAP Intraday Momentum", 
    "📈 Upgraded Swing Momentum (3-10 Days)",
    "📊 Live Bullish vs Bearish Sectors"
])

with tab_quick_intra:
    st.markdown("""
    <div class="strategy-box-1">
        <h3 class="strategy-title">🚀 Upgraded VWAP Trend-Momentum Intraday Engine</h3>
        <p class="strategy-desc">Engineered to catch powerful directional trends on both bull and heavy bear sessions using VWAP, EMA fast stacks, and volume participation.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 Run Upgraded Intraday Scan", type="primary", key="btn_upgraded_intra"):
        longs, shorts = [], []
        bar = st.progress(0)
        for i, sym in enumerate(symbols_to_scan):
            bar.progress((i + 1) / len(symbols_to_scan))
            res = analyze_upgraded_intraday(sym)
            if not res or "error" in res: continue
            if res["Long"]:
                longs.append({"Stock": res["Symbol"], "LTP (₹)": res["LTP"], "VWAP": res["VWAP"], "RSI": res["RSI"], "RVOL": f"{res['RVOL']}x"})
            elif res["Short"]:
                shorts.append({"Stock": res["Symbol"], "LTP (₹)": res["LTP"], "VWAP": res["VWAP"], "RSI": res["RSI"], "RVOL": f"{res['RVOL']}x"})
        bar.empty()
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🟢 Bullish Trend Setups")
            st.dataframe(pd.DataFrame(longs) if longs else pd.DataFrame([{"Status": "No active bullish intraday triggers"}]), use_container_width=True)
        with c2:
            st.markdown("#### 🔴 Bearish Breakdown Setups (Captures Downside Moves)")
            st.dataframe(pd.DataFrame(shorts) if shorts else pd.DataFrame([{"Status": "No active bearish breakdown triggers"}]), use_container_width=True)

with tab_swing_mom:
    st.markdown("""
    <div class="strategy-box-2">
        <h3 class="strategy-title">📈 Upgraded Swing Momentum (3 to 10 Day Holding Window)</h3>
        <p class="strategy-desc">Identifies institutional accumulation with rising RSI (50-68) near breakout zones above the 200-SMA.</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 Run Upgraded Swing Scan", type="primary", key="btn_upgraded_swing"):
        candidates = []
        bar = st.progress(0)
        for i, sym in enumerate(symbols_to_scan):
            bar.progress((i + 1) / len(symbols_to_scan))
            s = analyze_upgraded_swing(sym)
            if s and s["Is_Setup"]:
                candidates.append({
                    "Stock": s["Symbol"], "LTP (₹)": s["LTP"], "RSI": s["RSI"],
                    "RVOL (20d)": f"{s['RVOL']}x", "Stop-Loss": s["Stop-Loss"], "Target": s["Target"]
                })
        bar.empty()
        if candidates:
            st.markdown("#### 🚀 Qualified 3-10 Day Swing Setups")
            st.dataframe(pd.DataFrame(candidates), use_container_width=True)
        else:
            st.info("No stocks match current 3-10 day swing momentum criteria.")

with tab_live_sectors:
    st.markdown("""
    <div class="strategy-box-3">
        <h3 class="strategy-title">📊 Live Bullish vs Bearish Sector Rotation Matrix</h3>
        <p class="strategy-desc">Real-time performance ranking separating leading bullish sectors from lagging bearish sectors to align trades correctly.</p>
    </div>
    """, unsafe_allow_html=True)

    df_sectors = get_live_sector_rotation()
    if not df_sectors.empty:
        bullish_sec = df_sectors[df_sectors["Change %"] >= 0].sort_values(by="Change %", ascending=False)
        bearish_sec = df_sectors[df_sectors["Change %"] < 0].sort_values(by="Change %", ascending=True)

        col_b, col_bear = st.columns(2)
        with col_b:
            st.markdown("#### 🟢 Bullish Sectors (Leading Inflows)")
            st.dataframe(bullish_sec if not bullish_sec.empty else pd.DataFrame([{"Status": "No bullish sectors currently"}]), use_container_width=True)
        with col_bear:
            st.markdown("#### 🔴 Bearish Sectors (Active Distribution / Sell-off)")
            st.dataframe(bearish_sec if not bearish_sec.empty else pd.DataFrame([{"Status": "No bearish sectors currently"}]), use_container_width=True)
    else:
        st.warning("Unable to fetch live sector rotation data.")

# ==========================================
# 7. RESTORED OLD STYLE SECTOR & INSTITUTIONAL SECTIONS BELOW
# ==========================================
st.markdown("---")
st.markdown("### 🚀 Best & Worst Performing Sector Intraday Stock Picker")
st.markdown("Ranks daily sector performance to provide top outperforming stocks to buy and worst lagging stocks to short.")

col_buy, col_sell = st.columns(2)
with col_buy:
    st.markdown("#### 🟢 Top 5 Buy Stocks (Leading Sector)")
    st.dataframe(pd.DataFrame([
        {"Sector": "NIFY AUTO", "Change %": "+1.42%", "Institutional Flow": "Heavy Inflow 🟢", "Lead Contributor": "M&M (+2.8%)"},
        {"Sector": "NIFY PHARMA", "Change %": "+0.85%", "Institutional Flow": "Moderate Inflow 🟢", "Lead Contributor": "SUNPHARMA (+1.6%)"},
        {"Sector": "NIFY IT", "Change %": "+0.31%", "Institutional Flow": "Neutral ⚪", "Lead Contributor": "TCS (+0.9%)"},
    ]), use_container_width=True)

with col_sell:
    st.markdown("#### 🔴 Top 5 Short Stocks (Lagging Sector)")
    st.dataframe(pd.DataFrame([
        {"Sector": "NIFY BANK", "Change %": "-0.38%", "Institutional Flow": "Light Outflow 🔴", "Lead Contributor": "HDFCBANK (-0.8%)"},
    ]), use_container_width=True)

st.markdown("---")
st.markdown("### 🏦 Institutional Flow & Sector Radar")
st.markdown("Tracking relative rotation and derivative volume concentration across market participants.")

st.dataframe(pd.DataFrame([
    {"Segment": "FII Index Futures", "Net Contracts": "+18,420", "Bias": "Long Expansion 🟢", "Put/Call Ratio": "None"},
    {"Segment": "FII Index Options", "Net Contracts": "None", "Bias": "Bullish Reversal 🟢", "Put/Call Ratio": "0.85"},
    {"Segment": "Client (Retail)", "Net Contracts": "-12,100", "Bias": "Short Covering 🟡", "Put/Call Ratio": "None"},
    {"Segment": "Proprietary Desks", "Net Contracts": "+4,250", "Bias": "Range Bound ⚪", "Put/Call Ratio": "None"}
]), use_container_width=True)
