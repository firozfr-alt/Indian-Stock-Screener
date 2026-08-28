import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from google import genai
import requests
import time

st.set_page_config(page_title="AI Multi-Horizon Indian Stock Screener", layout="wide")
st.title("🏛️ Multi-Horizon & Fundamental Compounder Screener")
st.caption("Automated Multi-Horizon Screening with Auto-Healing AI Agents & Rate Limit Protection")

# =========================================================
# INITIALIZE NEW GEMINI API & AUTO-DISCOVER MODEL
# =========================================================
if "GEMINI_API_KEY" in st.secrets:
    try:
        ai_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        # We start with the known stable model identifier
        ai_model_name = 'gemini-2.5-flash'
        st.sidebar.success(f"✅ AI Core Active ({ai_model_name})")
    except Exception as e:
        ai_client = None
        st.sidebar.error(f"🚨 Failed to initialize AI Client: {e}")
else:
    ai_client = None
    st.sidebar.error("🚨 Missing GEMINI_API_KEY in Streamlit Secrets")

# Top 5 Core Indian Sectors Universe
UNIVERSE = {
    "Banking & Financials": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "BAJFINANCE.NS"],
    "Information Technology": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "LTIM.NS", "PERSISTENT.NS"],
    "Automotive & Ancillary": ["TATAMOTORS.NS", "M&M.NS", "MARUTI.NS", "BAJAJ-AUTO.NS", "TVSMOTOR.NS"],
    "Pharma & Healthcare": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "ZYDUSLIFE.NS"],
    "FMCG & Consumption": ["ITC.NS", "HUL.NS", "NESTLEIND.NS", "BRITANNIA.NS", "VBL.NS"]
}

# =========================================================
# AGENT 1: ROBUST FUNDAMENTALS EXTRACTOR
# =========================================================
@st.cache_data(ttl=1800)
def extract_complete_metrics(ticker, sector_name):
    """Pulls momentum and financial data without hitting web scrapers."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if hist.empty or len(hist) < 30:
            return None
            
        close = hist['Close']
        current_price = float(close.iloc[-1])
        
        # Momentum
        ret_1m = float(((current_price - close.iloc[-min(22, len(close))]) / close.iloc[-min(22, len(close))]) * 100)
        ret_6m = float(((current_price - close.iloc[-min(126, len(close))]) / close.iloc[-min(126, len(close))]) * 100)
        
        info = stock.info or {}
        pe = info.get('trailingPE')
        roe = info.get('returnOnEquity')
        
        roe_val = round(roe * 100, 2) if roe is not None else 15.0
        pe_val = round(pe, 2) if pe is not None else 25.0

        score = 0
        if roe_val >= 15.0: score += 3
        if 0 < pe_val <= 45: score += 2
        if ret_6m > 10.0: score += 2

        return {
            "Symbol": ticker.replace(".NS", ""),
            "Sector": sector_name,
            "Price (₹)": round(current_price, 2),
            "1M (%)": round(ret_1m, 2),
            "6M (%)": round(ret_6m, 2),
            "P/E": pe_val,
            "ROE (%)": roe_val,
            "Score (/10)": min(10, score)
        }
    except Exception:
        return None

# =========================================================
# AGENT 2: AI MULTI-HORIZON COMMITTEE (WITH RETRY & FALLBACK)
# =========================================================
def run_ai_horizon_thesis_with_retry(stock_data, target_horizon, max_retries=3):
    if not ai_client: return "AI offline."
    
    prompt = f"""
    Analyze {stock_data['Symbol']} (Sector: {stock_data['Sector']}) for a {target_horizon} horizon.
    Metrics: Price ₹{stock_data['Price (₹)']}, 1M: {stock_data['1M (%)']}%, 6M: {stock_data['6M (%)']}%, P/E: {stock_data['P/E']}, ROE: {stock_data['ROE (%)']}%.
    Provide: 1) Core Strength for this horizon, 2) Key Risk, 3) Final Verdict (STRONG BUY, ACCUMULATE, HOLD). Keep it concise.
    """
    
    # Exponential Backoff Loop for Rate Limits (429)
    for attempt in range(max_retries):
        try:
            # Using the new google-genai SDK format
            response = ai_client.models.generate_content(
                model=ai_model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "quota" in error_msg or "rate" in error_msg or "exhausted" in error_msg:
                wait_time = (attempt + 1) * 15 # Wait 15s, then 30s
                st.toast(f"Rate limit hit on {stock_data['Symbol']}. Pausing {wait_time}s...")
                time.sleep(wait_time)
            elif "404" in error_msg or "not found" in error_msg:
                return f"Model alias deprecated by Google. Please update ai_model_name in code."
            else:
                return f"AI Generation Failed: {e}"
                
    # If we run out of retries, you can optionally route to a free OpenRouter backup here
    return "AI Evaluation failed: Rate limit exceeded after maximum retries. Try analyzing fewer stocks at once."

# =========================================================
# DASHBOARD UI WORKFLOW
# =========================================================
st.sidebar.header("🎯 Screener Filters")
selected_horizon = st.sidebar.radio(
    "Target Holding Horizon:",
    ["6M+ (Long-Term Quality Compounder)", "3 Months (Quarterly Swing)"]
)
max_ai_evaluations = st.sidebar.slider("Max Stocks to run through AI (Protects Quota)", 1, 5, 3)

if st.button("🚀 Run Multi-Horizon Screener"):
    with st.spinner("Analyzing price action and balance sheets..."):
        all_data = []
        for sector, tickers in UNIVERSE.items():
            for t in tickers:
                res = extract_complete_metrics(t, sector)
                if res:
                    all_data.append(res)
                time.sleep(0.2) # Light sleep for yfinance
                
        df = pd.DataFrame(all_data)

    if not df.empty:
        df_sorted = df.sort_values(by=["Score (/10)", "6M (%)"], ascending=[False, False]).reset_index(drop=True)
        st.subheader("📊 Fundamental & Momentum Matrix")
        st.dataframe(df_sorted, use_container_width=True)

        st.subheader(f"🏛️ AI Committee Verdicts for: **{selected_horizon}**")
        
        # We limit the number of AI calls to prevent instant 429 Quota blocks
        top_candidates = df_sorted.head(max_ai_evaluations).to_dict('records')
        
        with st.spinner("Generative AI Committee reviewing top candidates (handling rate limits safely)..."):
            for candidate in top_candidates:
                # Calls the new robust function with the backoff loop
                thesis = run_ai_horizon_thesis_with_retry(candidate, selected_horizon)
                
                with st.expander(
                    f"📌 {candidate['Symbol']} ({candidate['Sector']}) — Score: {candidate['Score (/10)']}/10 | ROE: {candidate['ROE (%)']}%", 
                    expanded=True
                ):
                    st.markdown(thesis)
                
                # Mandatory cooldown between successful calls to stay under Free Tier limits
                time.sleep(4)
