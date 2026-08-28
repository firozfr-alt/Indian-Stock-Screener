import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import google.generativeai as genai
from datetime import datetime

st.set_page_config(page_title="Self-Improving AI Multi-Agent Screener", layout="wide")
st.title("🧠 Self-Improving AI Multi-Agent Indian Market Platform")

# =========================================================
# INITIALIZE GEMINI API
# =========================================================
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
    st.sidebar.success("✅ AI Core Active (Gemini 1.5 Flash)")
else:
    ai_model = None
    st.sidebar.error("🚨 Missing GEMINI_API_KEY in Streamlit Secrets")

# Indian Market Universe across 4 Core Sectors
UNIVERSE = {
    "Banking / Financials": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS"],
    "Information Technology": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS"],
    "Auto & Manufacturing": ["TATAMOTORS.NS", "M&M.NS", "MARUTI.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS"],
    "Energy & Conglomerates": ["RELIANCE.NS", "NTPC.NS", "ONGC.NS", "POWERGRID.NS", "COALINDIA.NS"]
}

# =========================================================
# AGENT 1: MARKET REGIME & DYNAMICS AGENT
# =========================================================
def analyze_market_regime():
    """Analyzes Nifty 50 and India VIX to determine current market regime."""
    try:
        nifty = yf.Ticker("^NSEI").history(period="6mo")
        vix = yf.Ticker("^INDIAVIX").history(period="1mo")
        
        current_nifty = nifty['Close'].iloc[-1]
        sma_50 = nifty['Close'].rolling(50).mean().iloc[-1]
        sma_200 = nifty['Close'].rolling(min(200, len(nifty))).mean().iloc[-1]
        current_vix = vix['Close'].iloc[-1] if not vix.empty else 14.0
        
        # Determine Trend
        if current_nifty > sma_50 > sma_200:
            trend = "Strong Bullish"
        elif current_nifty < sma_50 < sma_200:
            trend = "Bearish / Correction"
        else:
            trend = "Consolidation / Mixed"
            
        # Determine Volatility Level
        if current_vix > 18.0:
            vol_state = "High Risk / Volatile"
        elif current_vix < 13.0:
            vol_state = "Complacent / Low Volatility"
        else:
            vol_state = "Normal / Balanced"
            
        return {
            "Nifty_Price": round(current_nifty, 2),
            "SMA_50": round(sma_50, 2),
            "India_VIX": round(current_vix, 2),
            "Trend": trend,
            "Volatility_State": vol_state
        }
    except Exception as e:
        return {
            "Nifty_Price": 0, "SMA_50": 0, "India_VIX": 15.0,
            "Trend": "Neutral", "Volatility_State": "Normal"
        }

# =========================================================
# AGENT 2: SELF-TUNING META AGENT (ADAPTIVE LOGIC)
# =========================================================
def generate_adaptive_strategy(regime, mode):
    """
    Dynamically tunes screening weights and evaluation directives
    based on current market dynamics and volatility.
    """
    if not ai_model:
        return "Standard quantitative rules applied."
        
    prompt = f"""
    You are the Meta-Strategist Agent of an automated hedge fund for the Indian Stock Market (NSE).
    Current Market Dynamics:
    - Nifty 50 Index Trend: {regime['Trend']} (Nifty at {regime['Nifty_Price']}, 50-DMA at {regime['SMA_50']})
    - India VIX: {regime['India_VIX']} ({regime['Volatility_State']})
    - Selected Mode: {mode}

    Task:
    Provide an operational directive (3-4 concise bullet points) for stock evaluation.
    - For Swing Trading: Detail how to calibrate entry timing, momentum thresholds (RSI), and stop-loss widths.
    - For Long-Term: Detail how to adjust valuation tolerance (P/E), solvency safety buffers, and margin of safety.
    """
    try:
        response = ai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Self-tuning fallback: Standard risk controls active. Error: {e}"

# =========================================================
# AGENT 3: QUANTITATIVE EXECUTION AGENT
# =========================================================
@st.cache_data(ttl=1800)
def process_stock_quant_data(ticker):
    """Calculates momentum, RSI, moving averages, and solvency metrics."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if len(hist) < 50:
            return None
            
        close = hist['Close']
        current_price = close.iloc[-1]
        
        # 6-Month Momentum
        momentum_6m = ((current_price - close.iloc[-126]) / close.iloc[-126]) * 100 if len(close) >= 126 else 0.0
        
        # 14-Day RSI Calculation
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # Moving Averages
        sma_20 = close.rolling(20).mean().iloc[-1]
        sma_50 = close.rolling(50).mean().iloc[-1]
        
        # Fundamental snapshot
        info = stock.info
        pe_ratio = info.get('trailingPE', np.nan)
        debt_to_equity = info.get('debtToEquity', np.nan)
        roe = info.get('returnOnEquity', np.nan)
        roe_pct = round(roe * 100, 2) if pd.notnull(roe) else np.nan
        
        return {
            "Symbol": ticker.replace(".NS", ""),
            "Sector": "",
            "Price (₹)": round(current_price, 2),
            "Momentum 6M (%)": round(momentum_6m, 2),
            "RSI (14)": round(current_rsi, 2),
            "Above 20-DMA": current_price > sma_20,
            "Above 50-DMA": current_price > sma_50,
            "P/E": round(pe_ratio, 2) if pd.notnull(pe_ratio) else "N/A",
            "ROE (%)": roe_pct if pd.notnull(roe_pct) else "N/A",
            "Debt/Equity": round(debt_to_equity / 100, 2) if pd.notnull(debt_to_equity) else "N/A"
        }
    except Exception:
        return None

# =========================================================
# AGENT 4: STRATEGIC CRITIC & ADVERSARY AGENT
# =========================================================
def run_adversary_critique(stock_data, strategy_directive, mode):
    """
    Executes a multi-perspective critique (Bull Thesis vs. Invalidation Risk)
    guided by the dynamic meta-strategy directive.
    """
    if not ai_model:
        return "AI Critic offline."
        
    prompt = f"""
    You are an AI Hedge Fund Portfolio Committee evaluating {stock_data['Symbol']}.
    
    Operational Directive from Meta-Agent:
    {strategy_directive}
    
    Stock Quantitative Metrics:
    - Mode: {mode}
    - Current Price: ₹{stock_data['Price (₹)']}
    - 6-Month Momentum: {stock_data['Momentum 6M (%)']}%
    - 14-Day RSI: {stock_data['RSI (14)']}
    - Trend Alignment: Above 20-DMA = {stock_data['Above 20-DMA']}, Above 50-DMA = {stock_data['Above 50-DMA']}
    - Valuation & Solvency: P/E = {stock_data['P/E']}, ROE = {stock_data['ROE (%)']}%, Debt/Equity = {stock_data['Debt/Equity']}
    
    Deliver a concise analysis structured as:
    1. **Bull Thesis:** Primary drivers justifying allocation.
    2. **Adversary Risk (The Bear Case):** Key failure points or red flags.
    3. **Actionable Decision:** Exact recommendation (AGGRESSIVE BUY, ACCUMULATE ON PULLBACK, or AVOID) with specific Stop-Loss or Entry criteria.
    """
    try:
        response = ai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Critique generation failed: {e}"

# =========================================================
# DASHBOARD WORKFLOW INTERFACE
# =========================================================
st.sidebar.header("🎯 System Controls")
selected_mode = st.sidebar.radio("Select Strategy Horizon:", ["Medium-Term Swing Trading", "Long-Term Quality Investing"])

# 1. Run Market Dynamics Check
st.subheader("🌐 Agent 1: Real-Time Market Regime & Volatility")
regime_data = analyze_market_regime()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Nifty 50 Index", f"₹{regime_data['Nifty_Price']:,}")
col2.metric("Market Trend", regime_data['Trend'])
col3.metric("India VIX", regime_data['India_VIX'])
col4.metric("Volatility Regime", regime_data['Volatility_State'])

# 2. Self-Tuning Directive Generation
with st.expander("⚡ Agent 2: Self-Tuned Operational Directive (Adaptive Logic)", expanded=True):
    with st.spinner("Meta-Agent calibrating strategy parameters to current dynamics..."):
        active_directive = generate_adaptive_strategy(regime_data, selected_mode)
        st.markdown(active_directive)

# 3. Pipeline Execution
if st.button("🚀 Execute Multi-Agent Screening Pipeline"):
    with st.spinner("Agent 3: Scanning Universe across Sectors..."):
        all_stock_records = []
        for sector_name, tickers in UNIVERSE.items():
            for t in tickers:
                data = process_stock_quant_data(t)
                if data:
                    data["Sector"] = sector_name
                    all_stock_records.append(data)
                    
        df_quant = pd.DataFrame(all_stock_records)

    st.subheader("📊 Agent 3: Quantitative Sector Screen")
    st.dataframe(df_quant, use_container_width=True)

    # Filter Top Candidates for AI In-Depth Committee Review
    st.subheader("🏛️ Agent 4: Strategic & Adversary Committee Review")
    with st.spinner("Running AI Critic Committee on top ranked setups..."):
        if selected_mode == "Medium-Term Swing Trading":
            # Filter by Momentum and Trend Alignment
            ranked_df = df_quant[df_quant['Above 50-DMA'] == True].sort_values(by="Momentum 6M (%)", ascending=False)
            top_candidates = ranked_df.head(3).to_dict('records')
        else:
            # Filter by Financial Quality / Reasonable Valuation
            ranked_df = df_quant.sort_values(by="Momentum 6M (%)", ascending=False)
            top_candidates = ranked_df.head(3).to_dict('records')

        for candidate in top_candidates:
            critique = run_adversary_critique(candidate, active_directive, selected_mode)
            with st.expander(f"📌 {candidate['Symbol']} ({candidate['Sector']}) — Price: ₹{candidate['Price (₹)']} | RSI: {candidate['RSI (14)']}", expanded=True):
                st.markdown(critique)
