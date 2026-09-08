import streamlit as st
import pandas as pd
import numpy as np
import requests
import pytz
from datetime import datetime

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="Institutional Multi-Cap & Swing Terminal",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #f3f4f6; }
    .terminal-box {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 58, 138, 0.6) 100%);
        border: 1px solid rgba(59, 130, 246, 0.5);
        padding: 20px; border-radius: 14px; margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. UNIVERSE DEFINITIONS & UPSTOX KEYS
# ==========================================
MULTICAP_UNIVERSE = {
    "Large Cap": {"RELIANCE": "NSE_EQ|INE002A01018", "TCS": "NSE_EQ|INE467B01029", "HDFCBANK": "NSE_EQ|INE040A01034"},
    "Mid Cap": {"TATAPOWER": "NSE_EQ|INE245A01021", "TVSMOTOR": "NSE_EQ|INE494B01023", "PERSISTENT": "NSE_EQ|INE262H01021"},
    "Small Cap": {"KPITTECH": "NSE_EQ|INE04I01020", "OBEROIRLTY": "NSE_EQ|INE093I01010", "CEATLTD": "NSE_EQ|INE482A01020"},
    "Micro & Penny": {"SUZLON": "NSE_EQ|INE040H01021", "JPPOWER": "NSE_EQ|INE355C01023", "IDFCFIRSTB": "NSE_EQ|INE092T01019"}
}

SWING_UNIVERSE = {
    "NIFTY 50 SWING": {
        "RELIANCE": "NSE_EQ|INE002A01018",
        "INFY": "NSE_EQ|INE009A01021",
        "ICICIBANK": "NSE_EQ|INE090A01021",
        "SBIN": "NSE_EQ|INE062A01020",
        "AXISBANK": "NSE_EQ|INE238A01034"
    }
}

def get_upstox_token():
    try:
        return st.secrets["UPSTOX_ACCESS_TOKEN"]
    except:
        return None

def fetch_candles(instrument_key, interval="day", days=100):
    token = get_upstox_token()
    if not token:
        return pd.DataFrame()
    
    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {token}'}
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    
    if interval == "intraday":
        url = f"https://api.upstox.com/v2/historical-candle/intraday/{instrument_key}/15minute"
    else:
        url = f"https://api.upstox.com/v2/historical-candle/{instrument_key}/day/{to_date}/{from_date}"
        
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            candles = response.json().get("data", {}).get("candles", [])
            if candles:
                df = pd.DataFrame(candles, columns=["Datetime", "Open", "High", "Low", "Close", "Volume", "OI"])
                df["Datetime"] = pd.to_datetime(df["Datetime"])
                return df.sort_values("Datetime").reset_index(drop=True)
    except:
        pass
    return pd.DataFrame()

# ==========================================
# 3. AI STRATEGY ENGINES
# ==========================================
def evaluate_multicap(symbol, key, category):
    df = fetch_candles(key, interval="day", days=200)
    if df.empty or len(df) < 50:
        return {"Stock": symbol, "Category": category, "LTP": 0, "RSI": 0, "Verdict": "WATCH 🟡", "Rationale": "Insufficient Data Feed"}
    
    closes = df["Close"]
    ltp = float(closes.iloc[-1])
    sma_50 = float(closes.rolling(50).mean().iloc[-1])
    sma_200 = float(closes.rolling(200).mean().iloc[-1]) if len(df) >= 200 else sma_50
    
    delta = closes.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi = float(100 - (100 / (1 + (gain / loss))).iloc[-1])
    
    verdict = "WATCH 🟡"
    rationale = "Consolidating inside structural range."
    
    if category == "Micro & Penny":
        if ltp > sma_50 and rsi < 75:
            verdict = "BUY 🟢"
            rationale = "High momentum breakout in speculative basket."
        elif rsi > 80:
            verdict = "SELL 🔴"
            rationale = "Overbought blow-off top risk."
        else:
            verdict = "AVOID ⛔"
            rationale = "High volatility decay profile."
    else:
        if ltp > sma_50 and ltp > sma_200 and 45 <= rsi <= 70:
            verdict = "BUY 🟢"
            rationale = "Strong structural uptrend above key institutional moving averages."
        elif ltp < sma_200 and rsi < 40:
            verdict = "SELL 🔴"
            rationale = "Breaking down below long-term structural support."
        elif rsi > 75:
            verdict = "AVOID ⛔"
            rationale = "Extended valuation; risk of mean reversion."
            
    return {
        "Stock": symbol,
        "Category": category,
        "LTP": round(ltp, 2),
        "RSI": round(rsi, 1),
        "Verdict": verdict,
        "Rationale": rationale
    }

def evaluate_swing(symbol, key):
    df = fetch_candles(key, interval="day", days=60)
    if df.empty or len(df) < 20:
        return None
        
    closes = df["Close"]
    ltp = float(closes.iloc[-1])
    sma_20 = float(closes.rolling(20).mean().iloc[-1])
    
    # ATR calculation
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - closes.shift()).abs()
    low_close = (df["Low"] - closes.shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = float(tr.rolling(14).mean().iloc[-1])
    
    delta = closes.diff()
    rsi = float(100 - (100 / (1 + (delta.where(delta > 0, 0).rolling(14).mean() / (-delta.where(delta < 0, 0)).rolling(14).mean()))).iloc[-1])
    
    if ltp > sma_20 and 45 <= rsi <= 65:
        return {
            "Stock": symbol,
            "Horizon": "3-15 Days",
            "LTP": round(ltp, 2),
            "Stop-Loss": round(ltp - (1.5 * atr), 2),
            "Target": round(ltp + (2.5 * atr), 2),
            "Signal": "SWING BUY 🟢"
        }
    return None

# ==========================================
# 4. STREAMLIT USER INTERFACE & TABS
# ==========================================
st.markdown("### 🏛️ Institutional Multi-Cap & Swing Decision Terminal")

if not get_upstox_token():
    st.warning("⚠️ Upstox Access Token missing from Streamlit secrets. Please add `UPSTOX_ACCESS_TOKEN` to stream exchange feeds.")

tab_multicap, tab_swing = st.tabs(["🌐 Multi-Cap Long-Term AI Agent", "📈 3-15 Day Swing Trading Engine"])

with tab_multicap:
    st.markdown("""
    <div class="terminal-box">
        <p style="margin:0; color: #93c5fd;"><b>Multi-Cap Allocation AI:</b> Scans Large, Mid, Small, and Micro/Penny universes using fundamental trend analysis and technical filters to issue definitive <b>BUY, SELL, AVOID, WATCH</b> verdicts.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Run Multi-Cap AI Evaluation", type="primary", key="btn_multi"):
        results = []
        bar = st.progress(0)
        total_items = sum(len(stocks) for stocks in MULTICAP_UNIVERSE.values())
        idx = 0
        
        for category, stocks in MULTICAP_UNIVERSE.items():
            for sym, key in stocks.items():
                idx += 1
                bar.progress(idx / total_items)
                res = evaluate_multicap(sym, key, category)
                results.append(res)
        bar.empty()
        
        if results:
            st.dataframe(pd.DataFrame(results), use_container_width=True)
        else:
            st.warning("Unable to fetch data for evaluation.")

with tab_swing:
    st.markdown("""
    <div class="terminal-box">
        <p style="margin:0; color: #93c5fd;"><b>Swing Engine:</b> Evaluates 3 to 15-day holding windows utilizing daily moving averages, ATR volatility stops, and momentum indicators.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Run Swing Momentum Scan", type="primary", key="btn_swing"):
        results = []
        bar = st.progress(0)
        stocks = SWING_UNIVERSE["NIFTY 50 SWING"]
        total = len(stocks)
        
        for idx, (sym, key) in enumerate(stocks.items()):
            bar.progress((idx + 1) / total)
            res = evaluate_swing(sym, key)
            if res:
                results.append(res)
        bar.empty()
        
        if results:
            st.success(f"Generated {len(results)} high-probability swing setups.")
            st.dataframe(pd.DataFrame(results), use_container_width=True)
        else:
            st.warning("No swing setups match the strict 3-15 day momentum criteria today.")
