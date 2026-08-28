import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import google.generativeai as genai
from datetime import datetime

st.set_page_config(page_title="Self-Improving AI Long-Term Screener", layout="wide")
st.title("🧠 Long-Term Quality Compounder & AI Committee Screener")

# =========================================================
# INITIALIZE GEMINI API (UPDATED MODEL ENDPOINT)
# =========================================================
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Updated to the current stable free-tier model identifier
    ai_model = genai.GenerativeModel('gemini-2.5-flash')
    st.sidebar.success("✅ AI Core Active (Gemini Flash)")
else:
    ai_model = None
    st.sidebar.error("🚨 Missing GEMINI_API_KEY in Streamlit Secrets")

# Top Performing Sectors & 4 Long-Term Compounders Each
UNIVERSE = {
    "Financial Services & Banking": ["HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS", "BAJFINANCE.NS"],
    "Information Technology": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "LTIM.NS"],
    "Automotive & Manufacturing": ["TATAMOTORS.NS", "M&M.NS", "MARUTI.NS", "BAJAJ-AUTO.NS"],
    "Pharma & Healthcare": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS"]
}

# =========================================================
# AGENT 1: MARKET REGIME & DYNAMICS AGENT
# =========================================================
def analyze_market_regime():
    try:
        nifty = yf.Ticker("^NSEI").history(period="6mo")
        vix = yf.Ticker("^INDIAVIX").history(period="1mo")
        
        current_nifty = nifty['Close'].iloc[-1]
        sma_50 = nifty['Close'].rolling(50).mean().iloc[-1]
        sma_200 = nifty['Close'].rolling(min(200, len(nifty))).mean().iloc[-1]
        current_vix = vix['Close'].iloc[-1] if not vix.empty else 14.0
        
        if current_nifty > sma_50 > sma_200:
            trend = "Strong Bullish"
        elif current_nifty < sma_50 < sma_200:
            trend = "Bearish / Correction"
        else:
            trend = "Consolidation / Mixed"
            
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
    except Exception:
        return {
            "Nifty_Price": 0, "SMA_50": 0, "India_VIX": 15.0,
            "Trend": "Neutral", "Volatility_State": "Normal"
        }

# =========================================================
# AGENT 2: SELF-TUNING META AGENT
# =========================================================
def generate_adaptive_strategy(regime):
    if not ai_model:
        return "Standard long-term quality criteria applied."
        
    prompt = f"""
    You are the Chief Investment Strategist for a long-term equity portfolio focused on Indian compounders.
    Current Market Dynamics:
    - Nifty Trend: {regime['Trend']} (Nifty at {regime['Nifty_Price']}, 50-DMA at {regime['SMA_50']})
    - India VIX: {regime['India_VIX']} ({regime['Volatility_State']})

    Task:
    Provide 3 concise operational bullet points instructing how strict we should be regarding valuation (P/E multiples) and margin of safety given this exact macroeconomic environment.
    """
    try:
        response = ai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Fallback criteria active: Focus on pristine balance sheets and ROCE > 15%."

# =========================================================
# AGENT 3: QUANTITATIVE FUNDAMENTAL AGENT
# =========================================================
@st.cache_data(ttl=1800)
def process_long_term_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")
        if hist.empty: return None
        
        current_price = hist['Close'].iloc[-1]
        
        # Fundamental metrics extraction
        pe = info.get('trailingPE', np.nan)
        roe = info.get('returnOnEquity', np.nan)
        roce = info.get('returnOnCapitalEmployed', np.nan)
        debt_to_equity = info.get('debtToEquity', np.nan)
        
        roe_pct = round(roe * 100, 2) if pd.notnull(roe) else "N/A"
        roce_pct = round(roce * 100, 2) if pd.notnull(roce) else "N/A"
        de_ratio = round(debt_to_equity / 100, 2) if pd.notnull(debt_to_equity) else "N/A"
        
        return {
            "Symbol": ticker.replace(".NS", ""),
            "Sector": "",
            "Price (₹)": round(current_price, 2),
            "P/E Ratio": round(pe, 2) if pd.notnull(pe) else "N/A",
            "ROE (%)": roe_pct,
            "ROCE (%)": roce_pct,
            "Debt/Equity": de_ratio
        }
    except Exception:
        return None

# =========================================================
# AGENT 4: STRATEGIC CRITIC & ADVERSARY COMMITTEE
# =========================================================
def run_long_term_critique(stock_data, strategy_directive):
    if not ai_model:
        return "AI Critic offline."
        
    prompt = f"""
    You are an elite Long-Term Value Investing Committee analyzing {stock_data['Symbol']}.
    
    Macro Strategy Directive:
    {strategy_directive}
    
    Company Financial Metrics:
    - Current Price: ₹{stock_data['Price (₹)']}
    - P/E Ratio: {stock_data['P/E Ratio']}
    - ROE: {stock_data['ROE (%)']}%
    - ROCE: {stock_data['ROCE (%)']}%
    - Debt-to-Equity: {stock_data['Debt/Equity']}
    
    Evaluate this stock against core long-term investment pillars (Business Moat, Return Efficiency, Solvency/Balance Sheet Strength, and Valuation Margin of Safety).
    Provide your evaluation in 3 structured sections:
    1. **Business Quality & Moat Assessment**
    2. **Balance Sheet & Return Efficiency Risks**
    3. **Final Long-Term Verdict** (STRONG LONG-TERM COMPOUNDER, ACCUMULATE ON DIPS, or AVOID) with a justification.
    """
    try:
        response = ai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Committee review failed: {e}"

# =========================================================
# DASHBOARD INTERFACE
# =========================================================
st.subheader("🌐 Market Regime & Volatility Assessment")
regime_data = analyze_market_regime()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Nifty 50", f"₹{regime_data['Nifty_Price']:,}")
col2.metric("Market Trend", regime_data['Trend'])
col3.metric("India VIX", regime_data['India_VIX'])
col4.metric("Volatility State", regime_data['Volatility_State'])

with st.expander("⚡ Self-Tuned Long-Term Valuation & Safety Guidelines", expanded=True):
    with st.spinner("Calibrating macro strategy..."):
        active_directive = generate_adaptive_strategy(regime_data)
        st.markdown(active_directive)

if st.button("🚀 Run Top 4 Sectors & 16 Compounders Long-Term Analysis"):
    with st.spinner("Gathering structural fundamentals across the 4 core sectors..."):
        all_records = []
        for sector_name, tickers in UNIVERSE.items():
            for t in tickers:
                data = process_long_term_stock(t)
                if data:
                    data["Sector"] = sector_name
                    all_records.append(data)
                    
        df_longterm = pd.DataFrame(all_records)

    st.subheader("📊 Fundamental Screener: Top Sectors & Stocks")
    st.dataframe(df_longterm, use_container_width=True)

    st.subheader("🏛️ AI Long-Term Committee Deep-Dive Reviews")
    with st.spinner("AI agents reviewing fundamental moats and valuations..."):
        for _, candidate in df_longterm.iterrows():
            critique = run_long_term_critique(candidate, active_directive)
            with st.expander(f"📌 {candidate['Symbol']} ({candidate['Sector']}) — P/E: {candidate['P/E Ratio']} | ROE: {candidate['ROE (%)']}%", expanded=False):
                st.markdown(critique)
