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
    page_title="Institutional Multi-Agent Terminal",
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
    .agent-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.2);
        padding: 15px; border-radius: 10px; margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. UNIVERSE DEFINITIONS & UPSTOX KEYS
# ==========================================
AGENT_UNIVERSES = {
    "Large-Cap Agent": {"RELIANCE": "NSE_EQ|INE002A01018", "TCS": "NSE_EQ|INE467B01029", "HDFCBANK": "NSE_EQ|INE040A01034"},
    "Mid-Cap Agent": {"TATAPOWER": "NSE_EQ|INE245A01021", "TVSMOTOR": "NSE_EQ|INE494B01023", "PERSISTENT": "NSE_EQ|INE262H01021"},
    "Small-Cap Agent": {"KPITTECH": "NSE_EQ|INE04I01020", "OBEROIRLTY": "NSE_EQ|INE093I01010", "CEATLTD": "NSE_EQ|INE482A01020"},
    "Micro & Penny Agent": {"SUZLON": "NSE_EQ|INE040H01021", "JPPOWER": "NSE_EQ|INE355C01023", "IDFCFIRSTB": "NSE_EQ|INE092T01019"}
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

def fetch_candles(instrument_key, interval="day", days=150):
    token = get_upstox_token()
    if not token:
        return pd.DataFrame()
    
    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {token}'}
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
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
# 3. MARKET OVERVIEW & AI AGENT ENGINES
# ==========================================
def get_market_overview():
    # Fetch Nifty 50 proxy for market regime
    df = fetch_candles("NSE_INDEX|Nifty 50", days=60) if "NSE_INDEX|Nifty 50" else fetch_candles("NSE_EQ|INE002A01018", days=60)
    if df.empty or len(df) < 20:
        return "Neutral 🟡", 0.0, "Data stream connecting..."
    
    closes = df["Close"]
    ltp = float(closes.iloc[-1])
    sma_20 = float(closes.rolling(20).mean().iloc[-1])
    pct_change = float(((ltp - closes.iloc[-2]) / closes.iloc[-2]) * 100)
    
    regime = "Bullish Uptrend 🟢" if ltp > sma_20 else "Bearish / Correction 🔴"
    summary = f"Market benchmark is currently trading {'above' if ltp > sma_20 else 'below'} its 20-day moving average with a daily change of {round(pct_change, 2)}%."
    return regime, round(pct_change, 2), summary

def run_agent_analysis(agent_name, stock_dict):
    agent_results = []
    for symbol, key in stock_dict.items():
        df = fetch_candles(key, days=120)
        if df.empty or len(df) < 30:
            agent_results.append({
                "Agent": agent_name, "Stock": symbol, "LTP": 0, "RSI": 0, 
                "Verdict": "WATCH 🟡", "Rationale": "Insufficient historical feed."
            })
            continue
            
        closes = df["Close"]
        ltp = float(closes.iloc[-1])
        sma_50 = float(closes.rolling(50).mean().iloc[-1])
        
        delta = closes.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = float(100 - (100 / (1 + (gain / loss))).iloc[-1])
        
        if agent_name == "Micro & Penny Agent":
            if ltp > sma_50 and rsi < 75:
                verdict, rationale = "BUY 🟢", "High momentum speculative expansion."
            elif rsi > 80:
                verdict, rationale = "SELL 🔴", "Overbought blow-off top risk."
            else:
                verdict, rationale = "AVOID ⛔", "High volatility consolidation decay."
        else:
            if ltp > sma_50 and 45 <= rsi <= 70:
                verdict, rationale = "BUY 🟢", "Solid institutional accumulation above 50 SMA."
            elif ltp < sma_50 and rsi < 40:
                verdict, rationale = "SELL 🔴", "Breaking structural support below 50 SMA."
            elif rsi > 75:
                verdict, rationale = "AVOID ⛔", "Overextended valuation range."
            else:
                verdict, rationale = "WATCH 🟡", "Consolidating within narrow channel."
                
        agent_results.append({
            "Agent": agent_name,
            "Stock": symbol,
            "LTP": round(ltp, 2),
            "RSI": round(rsi, 1),
            "Verdict": verdict,
            "Rationale": rationale
        })
    return agent_results

def evaluate_swing(symbol, key):
    df = fetch_candles(key, days=60)
    if df.empty or len(df) < 20:
        return None
        
    closes = df["Close"]
    ltp = float(closes.iloc[-1])
    sma_20 = float(closes.rolling(20).mean().iloc[-1])
    
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
            "Holding Period": "3-15 Days",
            "LTP": round(ltp, 2),
            "Stop-Loss": round(ltp - (1.5 * atr), 2),
            "Target": round(ltp + (2.5 * atr), 2),
            "Signal": "SWING BUY 🟢"
        }
    return None

# ==========================================
# 4. STREAMLIT USER INTERFACE & TABS
# ==========================================
st.markdown("### 🏛️ Institutional Multi-Agent & Market Terminal")

if not get_upstox_token():
    st.warning("⚠️ Upstox Access Token missing from Streamlit secrets. Please add `UPSTOX_ACCESS_TOKEN` to stream live market feeds.")

# Market Overview Section
regime, daily_pct, overview_text = get_market_overview()
col1, col2, col3 = st.columns(3)
col1.metric("Market Regime", regime, f"{daily_pct}%")
col2.metric("Active AI Agents", "4 Specialized Models", "Online")
col3.metric("Data Pipeline", "Upstox REST API", "Active")

st.markdown("---")

tab_agents, tab_swing = st.tabs(["🤖 4-Agent Long-Term Multi-Cap Terminal", "📈 3-15 Day Swing Trading Engine"])

with tab_agents:
    st.markdown("""
    <div class="terminal-box">
        <h4 style="color: #60a5fa; margin-top:0;">Multi-Cap AI Committee (Large, Mid, Small, Micro/Penny)</h4>
        <p style="margin:0; color: #cbd5e1;">Four specialized AI screening agents evaluate respective capital tiers in parallel, delivering definitive <b>BUY, SELL, AVOID, WATCH</b> verdicts based on momentum, moving averages, and volatility parameters.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Run All 4 AI Agents Analysis", type="primary", key="btn_agents"):
        all_agent_outputs = []
        bar = st.progress(0)
        total_agents = len(AGENT_UNIVERSES)
        
        for idx, (agent_name, universe) in enumerate(AGENT_UNIVERSES.items()):
            bar.progress((idx + 1) / total_agents)
            res = run_agent_analysis(agent_name, universe)
            all_agent_outputs.extend(res)
        bar.empty()
        
        if all_agent_outputs:
            df_results = pd.DataFrame(all_agent_outputs)
            
            # Display by Agent in clean expanders or tables
            for agent_name in AGENT_UNIVERSES.keys():
                st.markdown(f"#### 🔎 {agent_name} Report")
                subset_df = df_results[df_results["Agent"] == agent_name].drop(columns=["Agent"])
                st.dataframe(subset_df, use_container_width=True)
        else:
            st.warning("Could not generate agent verdicts. Verify Upstox API credentials.")

with tab_swing:
    st.markdown("""
    <div class="terminal-box">
        <h4 style="color: #60a5fa; margin-top:0;">Short-to-Medium Swing Engine (3 to 15 Days)</h4>
        <p style="margin:0; color: #cbd5e1;">Optimized for swing traders holding positions between 3 and 15 days using ATR volatility brackets and 20-day trend filters.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Run 3-15 Day Swing Momentum Scan", type="primary", key="btn_swing_scan"):
        swing_results = []
        bar = st.progress(0)
        stocks = SWING_UNIVERSE["NIFTY 50 SWING"]
        total = len(stocks)
        
        for idx, (sym, key) in enumerate(stocks.items()):
            bar.progress((idx + 1) / total)
            res = evaluate_swing(sym, key)
            if res:
                swing_results.append(res)
        bar.empty()
        
        if swing_results:
            st.success(f"Identified {len(swing_results)} high-conviction swing setups for the 3-15 day window.")
            st.dataframe(pd.DataFrame(swing_results), use_container_width=True)
        else:
            st.warning("No stocks match the strict 3-15 day swing criteria under current market conditions.")
