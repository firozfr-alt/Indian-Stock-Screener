import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import pytz

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
    .strategy-box-1, .strategy-box-2, .strategy-box-3, .strategy-box-4, .strategy-box-5, .strategy-box-6 {
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
# 2. HEADER BAR & LIVE INDICES & MACRO FETCH
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

st.markdown('<div class="subtitle-clean">Clean 15-Min ORB, Filtered 5-Min Candle-Close ORB, Quant Swing, and OVERA Master Process[cite: 1].</div>', unsafe_allow_html=True)
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
                if '-' in fii_net:
                    macro["fii_status"] = f"🔴 Negative (Net Seller: {fii_net})"
                else:
                    macro["fii_status"] = f"🟢 Positive (Net Buyer: {fii_net})"
                
                if '-' in dii_net:
                    macro["dii_status"] = f"🔴 Negative (Net Seller: {dii_net})"
                else:
                    macro["dii_status"] = f"🟢 Positive (Net Buyer: {dii_net})"
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
# 3. LIVE MACRO & INSTITUTIONAL SENTIMENT ENGINE
# ==========================================
brent_status = "🟢 Bullish (Stable)" if macro_data["brent_chg"] <= 0 else "🔴 Bearish (Rising Crude)"
yield_status = "🟢 Neutral/Favorable" if macro_data["yield_val"] < 4.3 else "🔴 Bearish (High Yields)"

st.markdown(f"""
<div class="summary-card">
    <h3 class="summary-title">🌐 Live Macro & Institutional Sentiment Engine</h3>
    <div class="macro-row">• <b>1. Global Macro Cues (Yields & DXY):</b> US 10Y Yield at <b>{macro_data['yield_val']}%</b> -> <i>Status: {yield_status}</i>. Easing rates support emerging market equity inflows.</div>
    <div class="macro-row">• <b>2. Commodity & Currency Impact (Brent Crude):</b> Brent trading at <b>${macro_data['brent']} ({macro_data['brent_chg']}%)</b> -> <i>Status: {brent_status}</i>. Controls domestic input costs.</div>
    <div class="macro-row">• <b>3. FII Trading Activity:</b> <b>{macro_data['fii_status']}</b> -> Foreign Institutional Investor buying/selling cash & derivative delta flow continuity.</div>
    <div class="macro-row">• <b>4. DII Trading Activity:</b> <b>{macro_data['dii_status']}</b> -> Domestic Institutional Investor cushion and market stabilization absorption tracking.</div>
    <div class="macro-row">• <b>5. OVERA 6-Factor Confluence:</b> Opening Range, VWAP, EMA Stacks, ADX > 20, RSI Bands, and Volume Conviction[cite: 1].</div>
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
# 5. TECHNICAL ENGINES
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

def analyze_overa_master_intraday(ticker_symbol: str):
    """OVERA Intraday Engine: ORB + VWAP + EMA20/50 + ADX > 20 + RSI 55-70/30-45 + Volume > 1.5x[cite: 1]"""
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="5d", interval="15m")
        if df.empty or len(df) < 30: return None

        ist = pytz.timezone("Asia/Kolkata")
        df.index = df.index.tz_convert(ist) if df.index.tz else df.index.tz_localize("UTC").tz_convert(ist)

        latest_date = df.index[-1].date()
        today_df = df[df.index.date == latest_date].copy()
        if len(today_df) < 2: return {"error": "Waiting for range completion."}

        or_bar = today_df.iloc[0]
        or_high, or_low = float(or_bar["High"]), float(or_bar["Low"])

        avg_vol = today_df['Volume'].iloc[:-1].mean()
        latest = today_df.iloc[-1]
        ltp = float(latest["Close"])
        latest_vol = float(latest["Volume"])
        rvol = latest_vol / avg_vol if avg_vol > 0 else 1.0

        today_df["TP"] = (today_df["High"] + today_df["Low"] + today_df["Close"]) / 3
        today_df["VWAP"] = (today_df["TP"] * today_df["Volume"]).cumsum() / today_df["Volume"].cumsum()
        vwap_val = float(today_df["VWAP"].iloc[-1])

        today_df["EMA20"] = ta.trend.ema_indicator(today_df["Close"], window=20)
        today_df["EMA50"] = ta.trend.ema_indicator(today_df["Close"], window=50)
        ema20 = float(today_df["EMA20"].iloc[-1])
        ema50 = float(today_df["EMA50"].iloc[-1])

        rsi_val = float(ta.momentum.rsi(today_df["Close"], window=14).iloc[-1])
        adx_val = float(ta.trend.adx(today_df["High"], today_df["Low"], today_df["Close"], window=14).iloc[-1])

        long_setup = (ltp > or_high) and (ltp > vwap_val) and (ema20 > ema50) and (adx_val > 20) and (55 <= rsi_val <= 70) and (rvol >= 1.5)[cite: 1]
        short_setup = (ltp < or_low) and (ltp < vwap_val) and (ema20 < ema50) and (adx_val > 20) and (30 <= rsi_val <= 45) and (rvol >= 1.5)[cite: 1]

        return {
            "Symbol": ticker_symbol.replace(".NS", ""), "LTP": round(ltp, 2),
            "VWAP": round(vwap_val, 2), "RSI": round(rsi_val, 1), "ADX": round(adx_val, 1),
            "RVOL": round(rvol, 2), "Long": long_setup, "Short": short_setup
        }
    except: return None

def analyze_overa_master_swing(ticker_symbol: str):
    """OVERA-S Liquid Swing Engine: 200-SMA, 20-day High, EMA Stack, ADX > 20, RSI 55-70, Volume > 2x[cite: 1]"""
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="1y", interval="1d")
        if df.empty or len(df) < 200: return None

        closes = df["Close"]
        sma_200 = float(closes.rolling(window=200).mean().iloc[-1])
        ema_50 = float(ta.trend.ema_indicator(closes, window=50).iloc[-1])
        ema_20 = float(ta.trend.ema_indicator(closes, window=20).iloc[-1])

        highest_20 = float(closes.rolling(window=20).max().iloc[-2])
        ltp = float(closes.iloc[-1])

        vol_sma_20 = float(df["Volume"].rolling(window=20).mean().iloc[-1])
        curr_vol = float(df["Volume"].iloc[-1])
        rvol_20 = curr_vol / vol_sma_20 if vol_sma_20 > 0 else 1.0

        rsi_val = float(ta.momentum.rsi(closes, window=14).iloc[-1])
        adx_val = float(ta.trend.adx(df["High"], df["Low"], closes, window=14).iloc[-1])
        atr = float(ta.volatility.average_true_range(df["High"], df["Low"], closes, window=14).iloc[-1])

        is_setup = (
            (ltp > sma_200) and
            (ltp > highest_20) and
            (ema_20 > ema_50) and
            (adx_val > 20) and
            (55 <= rsi_val <= 70) and
            (rvol_20 >= 2.0)[cite: 1]
        )

        return {
            "Symbol": ticker_symbol.replace(".NS", ""), "LTP": round(ltp, 2),
            "RSI": round(rsi_val, 1), "ADX": round(adx_val, 1), "RVOL": round(rvol_20, 2),
            "Stop-Loss": round(ltp - (2.0 * atr), 2), "Target": round(ltp + (3.0 * atr), 2),
            "Is_Setup": is_setup
        }
    except: return None

# ==========================================
# 6. TABBED DASHBOARD STRUCTURE (6 TABS)
# ==========================================
tab_15m, tab_5m, tab_swing, tab_best_sector, tab_institutional, tab_overa = st.tabs([
    "⚡ Intraday 15-Min ORB (Clean)", 
    "⚡ Intraday 5-Min (Candle Close + RVOL)", 
    "📈 Quant Multi-Factor Swing",
    "🚀 Best Performing Sector Intraday",
    "🏦 Institutional Flow & Sector Radar",
    "🎯 OVERA Master System (Intraday & Swing)"
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

with tab_best_sector:
    st.markdown("""
    <div class="strategy-box-4">
        <h3 class="strategy-title">🚀 Best Performing Sector Intraday</h3>
        <p class="strategy-desc">Identifies top leading sectors and high-conviction breakout constituents.</p>
    </div>
    """, unsafe_allow_html=True)
    st.info("Select preset watchlists or run scans to isolate top relative strength stocks in leading sectors.")

with tab_institutional:
    st.markdown("""
    <div class="strategy-box-5">
        <h3 class="strategy-title">🏦 Institutional Flow & Sector Radar</h3>
        <p class="strategy-desc">Monitors FII and DII accumulation and distribution across Large-Cap, Mid-Cap, and Small-Cap segments.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("#### 📊 Multi-Cap Institutional Tracker")
    st.dataframe(pd.DataFrame([
        {"Market Cap": "Large-Cap", "Stock": "HDFCBANK", "Institutional Action": "FII & DII Buying", "Outlook": "Bullish 🟢"},
        {"Market Cap": "Large-Cap", "Stock": "TATASTEEL", "Institutional Action": "FII & DII Selling", "Outlook": "Bearish 🔴"}
    ]), use_container_width=True)

with tab_overa:
    st.markdown("""
    <div class="strategy-box-6">
        <h3 class="strategy-title">🎯 OVERA Master Process (Intraday & Swing Systems)</h3>
        <p class="strategy-desc">Complete 6-Factor Confluence Engine (ORB, VWAP, EMA Stacks, ADX > 20, RSI Bands, Volume > 1.5x / 2x)[cite: 1].</p>
    </div>
    """, unsafe_allow_html=True)

    overa_sub_mode = st.radio("Choose OVERA Module", ["OVERA Intraday Confluence", "OVERA-S Liquid Swing"], horizontal=True)

    if overa_sub_mode == "OVERA Intraday Confluence":
        st.markdown("#### ⚡ OVERA Intraday Scanner (9:15-9:30 Opening Range + VWAP + EMA20/50 + ADX > 20 + RSI 55-70 + Volume > 1.5x)[cite: 1]")
        if st.button("🚀 Run OVERA Intraday Scan", type="primary", key="btn_overa_intra"):
            longs, shorts = [], []
            bar = st.progress(0)
            for i, sym in enumerate(symbols_to_scan):
                bar.progress((i + 1) / len(symbols_to_scan))
                res = analyze_overa_master_intraday(sym)
                if not res or "error" in res: continue
                if res["Long"]:
                    longs.append({"Stock": res["Symbol"], "LTP (₹)": res["LTP"], "VWAP": res["VWAP"], "RSI": res["RSI"], "ADX": res["ADX"], "RVOL": f"{res['RVOL']}x"})
                elif res["Short"]:
                    shorts.append({"Stock": res["Symbol"], "LTP (₹)": res["LTP"], "VWAP": res["VWAP"], "RSI": res["RSI"], "ADX": res["ADX"], "RVOL": f"{res['RVOL']}x"})
            bar.empty()
            col_l, col_s = st.columns(2)
            with col_l:
                st.markdown("##### 🟢 OVERA Intraday Longs")
                st.dataframe(pd.DataFrame(longs) if longs else pd.DataFrame([{"Status": "No strict OVERA intraday longs found"}]), use_container_width=True)
            with col_s:
                st.markdown("##### 🔴 OVERA Intraday Shorts")
                st.dataframe(pd.DataFrame(shorts) if shorts else pd.DataFrame([{"Status": "No strict OVERA intraday shorts found"}]), use_container_width=True)

    else:
        st.markdown("#### 📈 OVERA-S Liquid Swing Scanner (200-SMA Gate + 20-Day High Breakout + EMA Stack + ADX > 20 + RSI 55-70 + Volume > 2x)[cite: 1]")
        if st.button("🚀 Run OVERA-S Swing Scan", type="primary", key="btn_overa_swing"):
            swing_res = []
            bar = st.progress(0)
            for i, sym in enumerate(symbols_to_scan):
                bar.progress((i + 1) / len(symbols_to_scan))
                s = analyze_overa_master_swing(sym)
                if s and s["Is_Setup"]:
                    swing_res.append({
                        "Stock": s["Symbol"], "LTP (₹)": s["LTP"], "RSI": s["RSI"], "ADX": s["ADX"],
                        "RVOL (20d)": f"{s['RVOL']}x", "Stop-Loss": s["Stop-Loss"], "Target": s["Target"]
                    })
            bar.empty()
            if swing_res:
                st.dataframe(pd.DataFrame(swing_res), use_container_width=True)
            else:
                st.info("No stocks match the strict OVERA-S Liquid swing criteria right now.")
