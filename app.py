import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import pytz
import ta

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="Pro Trading Screener (Multi-Strategy)",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stDataFrame { border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Pro Indian Equity Screener: Intraday & Swing")
st.caption("Multi-strategy institutional platform featuring Clean 15-Min ORB, Filtered 5-Min Candle-Close ORB, and Quant Swing setups.")

# ==========================================
# 2. WATCHLISTS & SIDEBAR CONTROLS
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

st.sidebar.header("🎯 Master Settings")

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
st.sidebar.subheader("Intraday Filters")
rvol_mult = st.sidebar.slider("Min Intraday RVOL", 1.0, 5.0, 1.5, 0.1)
auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh (every 60s)", value=False)
if auto_refresh:
    st.sidebar.info("Auto-refresh active.")
    st.fragment(run_every=60)

st.sidebar.markdown("---")
st.sidebar.subheader("Swing Filters")
min_alpha = st.sidebar.slider("Min Swing Alpha Score", 0.8, 2.0, 1.2, 0.1)

# ==========================================
# 3. ENGINES (INTRADAY 15M, 5M & SWING)
# ==========================================
def analyze_orb_strategy(ticker_symbol: str, timeframe: str):
    """
    timeframe: '15m' for 15-min clean ORB (9:15-9:30)
              '5m' for 5-min candle-close confirmed ORB (9:15-9:20)
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        df = stock.history(period="14d", interval=timeframe)

        if df.empty or len(df) < 30:
            return None

        ist = pytz.timezone("Asia/Kolkata")
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC").tz_convert(ist)
        else:
            df.index = df.index.tz_convert(ist)

        # Historical Opening Volume Baseline
        first_candles = df.groupby(df.index.date).first()
        avg_opening_volume = first_candles['Volume'].iloc[:-1].mean()

        latest_date = df.index[-1].date()
        today_df = df[df.index.date == latest_date].copy()

        # Check required bars based on timeframe
        min_bars_required = 2 if timeframe == '15m' else 2
        if len(today_df) < min_bars_required:
            return {"error": "Waiting for range completion."}

        if timeframe == '15m':
            # 15-min range: First candle covers 9:15-9:30
            or_bar = today_df.iloc[0]
            or_high = float(or_bar["High"])
            or_low = float(or_bar["Low"])
            today_opening_vol = float(or_bar["Volume"])
            
            # Latest completed bar for check
            latest = today_df.iloc[-1]
            ltp = float(latest["Close"])
            # For 15m, check if current/latest close breaks range
            breakout_cond = (ltp > or_high)
            breakdown_cond = (ltp < or_low)
        else:
            # 5-min range: First bar is 9:15-9:20
            or_bar = today_df.iloc[0]
            or_high = float(or_bar["High"])
            or_low = float(or_bar["Low"])
            today_opening_vol = float(or_bar["Volume"])

            # Strict Candle Close Confirmation: Inspect second bar onwards
            sub_candles = today_df.iloc[1:]
            if sub_candles.empty:
                return {"error": "Waiting for breakout candle close."}
            
            latest = sub_candles.iloc[-1]
            ltp = float(latest["Close"])
            # Require the 5-min candle CLOSE to cross the boundaries (eliminating wick noise)
            breakout_cond = (float(latest["Close"]) > or_high)
            breakdown_cond = (float(latest["Close"]) < or_low)

        rvol = today_opening_vol / avg_opening_volume if avg_opening_volume > 0 else 1.0

        # VWAP Calculation for today
        today_df["TP"] = (today_df["High"] + today_df["Low"] + today_df["Close"]) / 3
        today_df["TPV"] = today_df["TP"] * today_df["Volume"]
        cum_tpv = today_df["TPV"].cumsum()
        cum_vol = today_df["Volume"].cumsum()
        today_df["VWAP"] = cum_tpv / cum_vol.replace(0, np.nan)
        vwap_latest = float(today_df["VWAP"].iloc[-1])

        return {
            "Symbol": ticker_symbol.replace(".NS", ""),
            "LTP": round(ltp, 2),
            "OR_High": round(or_high, 2),
            "OR_Low": round(or_low, 2),
            "VWAP": round(vwap_latest, 2),
            "RVOL": round(rvol, 2),
            "Breakout": breakout_cond,
            "Breakdown": breakdown_cond
        }
    except Exception:
        return None

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
        
        latest_idx = -1
        ltp = float(closes.iloc[latest_idx])
        alpha = float(alpha_score.iloc[latest_idx])
        z_val = float(z_price.iloc[latest_idx])
        rvol_val = float(rvol_20.iloc[latest_idx])
        
        atr = float(ta.volatility.average_true_range(df["High"], df["Low"], df["Close"], window=14).iloc[-1])
        is_setup = (alpha >= min_alpha) and (0.5 <= z_val <= 2.0) and (rvol_val >= 1.2)
        
        return {
            "Symbol": ticker_symbol.replace(".NS", ""),
            "LTP": round(ltp, 2),
            "Alpha Score": round(alpha, 2),
            "Z-Score": round(z_val, 2),
            "RVOL_20": round(rvol_val, 2),
            "ATR": round(atr, 2),
            "Is_Setup": is_setup
        }
    except: return None

# ==========================================
# 4. TABBED LAYOUT STRUCTURE (3 TABS)
# ==========================================
tab_15m, tab_5m, tab_swing = st.tabs([
    "⚡ Intraday 15-Min ORB (Clean)", 
    "⚡ Intraday 5-Min (Candle Close + RVOL)", 
    "📈 Quant Multi-Factor Swing"
])

# --- TAB 1: CLEAN 15-MIN ORB ---
with tab_15m:
    st.subheader("⚡ 15-Minute Opening Range Breakout (9:15–9:30 AM)")
    st.caption("Low-noise institutional strategy. Uses a 15-minute opening range to filter out early morning whipsaws.")

    if st.button("🚀 Run 15-Min Scan", type="primary", key="btn_15m"):
        buy_signals, sell_signals, neutral_list = [], [], []
        progress_bar = st.progress(0)
        status_msg = st.empty()

        for i, sym in enumerate(symbols_to_scan):
            status_msg.text(f"Scanning {sym} ({i+1}/{len(symbols_to_scan)})...")
            progress_bar.progress((i + 1) / len(symbols_to_scan))

            data = analyze_orb_strategy(sym, timeframe="15m")
            if not data or "error" in data:
                continue

            ltp, or_h, or_l, vwap, rvol = data["LTP"], data["OR_High"], data["OR_Low"], data["VWAP"], data["RVOL"]
            has_vol = rvol >= rvol_mult

            if data["Breakout"] and (ltp > vwap) and has_vol:
                sl = or_l
                risk = round(ltp - sl, 2)
                buy_signals.append({"Stock": data["Symbol"], "LTP (₹)": ltp, "OR High": or_h, "Stop-Loss": sl, "Target (1.5R)": round(ltp + (1.5 * risk), 2), "VWAP": vwap, "RVOL": f"{rvol}x"})
            elif data["Breakdown"] and (ltp < vwap) and has_vol:
                sl = or_h
                risk = round(sl - ltp, 2)
                sell_signals.append({"Stock": data["Symbol"], "LTP (₹)": ltp, "OR Low": or_l, "Stop-Loss": sl, "Target (1.5R)": round(ltp - (1.5 * risk), 2), "VWAP": vwap, "RVOL": f"{rvol}x"})
            else:
                neutral_list.append({"Stock": data["Symbol"], "LTP": ltp, "RVOL": f"{rvol}x"})

        status_msg.success("15-Min Scan Completed.")
        progress_bar.empty()

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🟢 15M BUY Setups")
            st.dataframe(pd.DataFrame(buy_signals) if buy_signals else pd.DataFrame([{"Status": "No Clean Breakouts"}]), use_container_width=True)
        with c2:
            st.markdown("### 🔴 15M SELL Setups")
            st.dataframe(pd.DataFrame(sell_signals) if sell_signals else pd.DataFrame([{"Status": "No Clean Breakdowns"}]), use_container_width=True)

# --- TAB 2: FILTERED 5-MIN CANDLE-CLOSE + RVOL ORB ---
with tab_5m:
    st.subheader("⚡ 5-Minute ORB with Strict Candle Close + RVOL")
    st.caption("Fights 5-minute noise by requiring a full candle to close outside the range boundaries, backed by high relative volume.")

    if st.button("🚀 Run Filtered 5-Min Scan", type="primary", key="btn_5m"):
        buy_signals, sell_signals, neutral_list = [], [], []
        progress_bar = st.progress(0)
        status_msg = st.empty()

        for i, sym in enumerate(symbols_to_scan):
            status_msg.text(f"Scanning {sym} ({i+1}/{len(symbols_to_scan)})...")
            progress_bar.progress((i + 1) / len(symbols_to_scan))

            data = analyze_orb_strategy(sym, timeframe="5m")
            if not data or "error" in data:
                continue

            ltp, or_h, or_l, vwap, rvol = data["LTP"], data["OR_High"], data["OR_Low"], data["VWAP"], data["RVOL"]
            has_vol = rvol >= rvol_mult

            if data["Breakout"] and (ltp > vwap) and has_vol:
                sl = or_l
                risk = round(ltp - sl, 2)
                buy_signals.append({"Stock": data["Symbol"], "LTP (₹)": ltp, "OR High": or_h, "Stop-Loss": sl, "Target (1.5R)": round(ltp + (1.5 * risk), 2), "VWAP": vwap, "RVOL": f"{rvol}x"})
            elif data["Breakdown"] and (ltp < vwap) and has_vol:
                sl = or_h
                risk = round(sl - ltp, 2)
                sell_signals.append({"Stock": data["Symbol"], "LTP (₹)": ltp, "OR Low": or_l, "Stop-Loss": sl, "Target (1.5R)": round(ltp - (1.5 * risk), 2), "VWAP": vwap, "RVOL": f"{rvol}x"})
            else:
                neutral_list.append({"Stock": data["Symbol"], "LTP": ltp, "RVOL": f"{rvol}x"})

        status_msg.success("Filtered 5-Min Scan Completed.")
        progress_bar.empty()

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🟢 Filtered 5M BUY Setups")
            st.dataframe(pd.DataFrame(buy_signals) if buy_signals else pd.DataFrame([{"Status": "No Confirmed Breakouts"}]), use_container_width=True)
        with c2:
            st.markdown("### 🔴 Filtered 5M SELL Setups")
            st.dataframe(pd.DataFrame(sell_signals) if sell_signals else pd.DataFrame([{"Status": "No Confirmed Breakdowns"}]), use_container_width=True)

# --- TAB 3: QUANTITATIVE SWING DASHBOARD ---
with tab_swing:
    st.subheader("📈 Quantitative Multi-Factor Swing Scanner")
    st.caption("Evaluates 60-day volatility-adjusted momentum, 50-day statistical Z-scores, and 20-day institutional RVOL accumulation.")
    
    if st.button("🚀 Run Quant Swing Scan", type="primary", key="btn_swing"):
        swing_candidates = []
        bar_s = st.progress(0)

        for i, sym in enumerate(symbols_to_scan):
            bar_s.progress((i + 1) / len(symbols_to_scan))
            s_data = analyze_swing_quant(sym)
            if s_data and s_data["Is_Setup"]:
                ltp, atr = s_data["LTP"], s_data["ATR"]
                swing_candidates.append({
                    "Stock": s_data["Symbol"], 
                    "LTP (₹)": ltp, 
                    "Alpha Score": s_data["Alpha Score"], 
                    "Z-Score": s_data["Z-Score"],
                    "RVOL (20d)": f"{s_data['RVOL_20']}x", 
                    "Stop-Loss": round(ltp - (2.0 * atr), 2), 
                    "Target": round(ltp + (3.0 * atr), 2)
                })
        bar_s.empty()

        if swing_candidates:
            df_swing = pd.DataFrame(swing_candidates).sort_values(by="Alpha Score", ascending=False)
            st.dataframe(df_swing, use_container_width=True)
            st.info("💡 **Swing Execution Rule:** Hold positions for 3 to 15 days. Trail your stop-loss along the rising moving average once the trade moves in your favor.")
        else:
            st.write("No swing setups match current quantitative alpha criteria.")
