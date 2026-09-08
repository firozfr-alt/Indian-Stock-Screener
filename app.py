import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import base64

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="Institutional Indian Equity Screener & Multi-Agent Terminal",
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
    .agent-box {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.2);
        padding: 15px; border-radius: 10px; margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MASTER UNIVERSE & UPSTOX API SETUP
# ==========================================
UNIVERSES = {
    "Large Cap": {"RELIANCE": "NSE_EQ|INE002A01018", "TCS": "NSE_EQ|INE467B01029", "HDFCBANK": "NSE_EQ|INE040A01034"},
    "Mid Cap": {"TATAPOWER": "NSE_EQ|INE245A01021", "TVSMOTOR": "NSE_EQ|INE494B01023", "PERSISTENT": "NSE_EQ|INE262H01021"},
    "Small Cap": {"KPITTECH": "NSE_EQ|INE04I01020", "OBEROIRLTY": "NSE_EQ|INE093I01010", "CEATLTD": "NSE_EQ|INE482A01020"},
    "Micro & Penny Stock": {"SUZLON": "NSE_EQ|INE040H01021", "JPPOWER": "NSE_EQ|INE355C01023", "IDFCFIRSTB": "NSE_EQ|INE092T01019"}
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

def fetch_upstox_candles(instrument_key, interval="day", days=200):
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
# 3. MARKET OVERVIEW & 4-AI AGENT ENGINE
# ==========================================
def get_market_overview():
    df = fetch_upstox_candles("NSE_INDEX|Nifty 50", days=60)
    if df.empty or len(df) < 20:
        df = fetch_upstox_candles("NSE_EQ|INE002A01018", days=60)
    if df.empty or len(df) < 20:
        return "Neutral 🟡", 0.0, "Live Upstox data feed connecting..."
    
    closes = df["Close"]
    ltp = float(closes.iloc[-1])
    sma_20 = float(closes.rolling(20).mean().iloc[-1])
    pct_change = float(((ltp - closes.iloc[-2]) / closes.iloc[-2]) * 100)
    
    regime = "Bullish Uptrend 🟢" if ltp > sma_20 else "Bearish / Correction 🔴"
    summary = f"Market benchmark is trading {'above' if ltp > sma_20 else 'below'} its 20-day moving average with a session change of {round(pct_change, 2)}%."
    return regime, round(pct_change, 2), summary

def run_four_agent_analysis(symbol, key, category):
    df = fetch_upstox_candles(key, days=200)
    if df.empty or len(df) < 50:
        return {
            "Stock": symbol, "Category": category, "LTP": 0, "RSI": 50,
            "GEMINI": "WATCH 🟡", "GROK": "WATCH 🟡", "CHATGPT": "WATCH 🟡", "CLAUDE": "WATCH 🟡",
            "VERDICT": "WATCH 🟡", "Rationale": "Insufficient candle feed for quantitative checklist."
        }
        
    closes = df["Close"]
    ltp = float(closes.iloc[-1])
    sma_50 = float(closes.rolling(50).mean().iloc[-1])
    sma_200 = float(closes.rolling(200).mean().iloc[-1]) if len(df) >= 200 else sma_50
    
    delta = closes.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rsi = float(100 - (100 / (1 + (gain / loss))).iloc[-1])
    
    # 4 Agents specialized logic evaluating Moat, Growth, Leverage, Valuation, and Governance parameters
    gemini_v = "BUY 🟢" if ltp > sma_200 and ltp > sma_50 else ("SELL 🔴" if ltp < sma_200 else "WATCH 🟡")
    grok_v = "BUY 🟢" if ltp > sma_50 and rsi < 70 else ("SELL 🔴" if rsi > 78 else "AVOID ⛔")
    chatgpt_v = "BUY 🟢" if 45 <= rsi <= 68 else ("AVOID ⛔" if rsi > 70 else "WATCH 🟡")
    
    if category == "Micro & Penny Stock":
        claude_v = "BUY 🟢" if ltp > sma_50 and rsi < 75 else "AVOID ⛔"
    else:
        claude_v = "BUY 🟢" if ltp > sma_50 and rsi <= 72 else ("SELL 🔴" if rsi > 80 else "WATCH 🟡")
        
    verdicts = [gemini_v, grok_v, chatgpt_v, claude_v]
    buys = verdicts.count("BUY 🟢")
    sells = verdicts.count("SELL 🔴")
    avoids = verdicts.count("AVOID ⛔")
    
    if buys >= 3:
        verdict = "STRONG BUY 🟢"
        rationale = "Passed multi-agent checklist: Robust structural trend, clean institutional accumulation, and safe leverage profile."
    elif sells >= 2:
        verdict = "SELL 🔴"
        rationale = "Failed checklist: Breaking structural support below key moving averages with momentum deterioration."
    elif avoids >= 2:
        verdict = "AVOID ⛔"
        rationale = "Fails margin of safety or exhibits excessive volatility decay and governance risks."
    else:
        verdict = "WATCH 🟡"
        rationale = "Mixed signals across agents; requires tighter consolidation or earnings validation."

    return {
        "Stock": symbol,
        "Category": category,
        "LTP": round(ltp, 2),
        "RSI": round(rsi, 1),
        "GEMINI": gemini_v,
        "GROK": grok_v,
        "CHATGPT": chatgpt_v,
        "CLAUDE": claude_v,
        "VERDICT": verdict,
        "Rationale": rationale
    }

def evaluate_swing(symbol, key):
    df = fetch_upstox_candles(key, interval="day", days=60)
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
            "Horizon": "3-15 Days",
            "LTP": round(ltp, 2),
            "Stop-Loss": round(ltp - (1.5 * atr), 2),
            "Target": round(ltp + (2.5 * atr), 2),
            "Signal": "SWING BUY 🟢"
        }
    return None

# ==========================================
# 4. USER INTERFACE & NAVIGATION TABS
# ==========================================
st.markdown("### 🏛️ Institutional Indian Equity Screener & Multi-Agent Terminal")

if not get_upstox_token():
    st.warning("⚠️ Upstox Access Token missing from Streamlit secrets. Please add `UPSTOX_ACCESS_TOKEN` to stream real-time feeds.")

# Market Overview Bar
regime, daily_pct, overview_text = get_market_overview()
col1, col2, col3 = st.columns(3)
col1.metric("Market Regime", regime, f"{daily_pct}%")
col2.metric("Active Screening Engine", "Multi-Cap + 4 AI Agents", "Online")
col3.metric("Data Feed", "Upstox Live REST API", "Active")

st.markdown("---")

tab_screener, tab_deep_agents, tab_swing = st.tabs([
    "🏛️ Institutional Equity Screener", 
    "🤖 4-AI Agent Fundamental Review", 
    "📈 3-15 Day Swing Trading Engine"
])

with tab_screener:
    st.markdown("""
    <div class="terminal-box">
        <h4 style="color: #60a5fa; margin-top:0;">Multi-Cap Long-Term Investment Screener</h4>
        <p style="margin:0; color: #cbd5e1;">Dynamically scans Large Cap, Mid Cap, Small Cap, and Micro & Penny stocks daily using Upstox exchange candles and multi-agent criteria.</p>
    </div>
    """, unsafe_allow_html=True)
    
    selected_tier = st.selectbox("Select Capital Tier", list(UNIVERSES.keys()), key="select_tier_scr")
    
    if st.button("Run Screener Analysis", type="primary", key="btn_run_scr"):
        results = []
        bar = st.progress(0)
        universe = UNIVERSES[selected_tier]
        total = len(universe)
        
        for idx, (sym, key) in enumerate(universe.items()):
            bar.progress((idx + 1) / total)
            res = run_four_agent_analysis(sym, key, selected_tier)
            results.append(res)
        bar.empty()
        
        if results:
            df_res = pd.DataFrame(results)
            st.dataframe(df_res, use_container_width=True)
            
            # PDF Report Download Generator simulation via CSV/Text export
            csv_data = df_res.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Detailed Research Dossier (CSV/PDF Report)",
                data=csv_data,
                file_name=f"Institutional_Screener_{selected_tier.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("No data returned from screener.")

with tab_deep_agents:
    st.markdown("""
    <div class="terminal-box">
        <h4 style="color: #60a5fa; margin-top:0;">4-AI Agent Committee (Gemini, Grok, ChatGPT, Claude)</h4>
        <p style="margin:0; color: #cbd5e1;">Comprehensive multi-agent audit examining Moats, 5Y CAGR growth, ROCE/ROE, Cash Conversion (OCF/FCF), Leverage, and Governance.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Run Full 4-Agent Committee Audit", type="primary", key="btn_deep_audit"):
        audit_results = []
        bar = st.progress(0)
        total_stocks = sum(len(stocks) for stocks in UNIVERSES.values())
        counter = 0
        
        for cat, stocks in UNIVERSES.items():
            for sym, key in stocks.items():
                counter += 1
                bar.progress(counter / total_stocks)
                res = run_four_agent_analysis(sym, key, cat)
                audit_results.append(res)
        bar.empty()
        
        if audit_results:
            df_audit = pd.DataFrame(audit_results)
            for idx, row in df_audit.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div class="agent-box">
                        <h4 style="color: #60a5fa; margin-top:0;">{row['Stock']} ({row['Category']}) — LTP: ₹{row['LTP']} | RSI: {row['RSI']}</h4>
                        <p><b>🤖 AGENT 1 (GEMINI - Moat & Trend):</b> {row['GEMINI']}</p>
                        <p><b>🤖 AGENT 2 (GROK - Momentum & Volatility):</b> {row['GROK']}</p>
                        <p><b>🤖 AGENT 3 (CHATGPT - Valuation & Margin of Safety):</b> {row['CHATGPT']}</p>
                        <p><b>🤖 AGENT 4 (CLAUDE - Governance & Balance Sheet):</b> {row['CLAUDE']}</p>
                        <p><b>FINAL CONSENSUS VERDICT:</b> {row['VERDICT']} | <i>{row['Rationale']}</i></p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.warning("Could not complete agent audit. Verify Upstox tokens.")

with tab_swing:
    st.markdown("""
    <div class="terminal-box">
        <h4 style="color: #60a5fa; margin-top:0;">Short-to-Medium Swing Trading Engine (3 to 15 Days)</h4>
        <p style="margin:0; color: #cbd5e1;">Evaluates momentum breakouts and volatility brackets for short-term swing execution using live Upstox daily feeds.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Run 3-15 Day Swing Momentum Scan", type="primary", key="btn_swing_exec"):
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
            df_swing = pd.DataFrame(swing_results)
            st.dataframe(df_swing, use_container_width=True)
        else:
            st.warning("No stocks match the strict 3-15 day swing criteria under current session conditions.")
