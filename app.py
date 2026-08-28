import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import google.generativeai as genai
import time

st.set_page_config(page_title="AI 10-Pillar Long-Term Screener", layout="wide")
st.title("🏛️ Long-Term Quality Compounder Screener (25-Stock Pipeline)")

# =========================================================
# INITIALIZE GEMINI API (UPDATED TO 2.5 FLASH)
# =========================================================
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    ai_model = genai.GenerativeModel('gemini-2.5-flash')
    st.sidebar.success("✅ AI Core Active (Gemini 2.5 Flash)")
else:
    ai_model = None
    st.sidebar.error("🚨 Missing GEMINI_API_KEY in Streamlit Secrets")

# =========================================================
# INDIAN MARKET SECTOR UNIVERSE (BROAD LIST)
# =========================================================
SECTOR_MAP = {
    "^NSEBANK": {"name": "Banking", "stocks": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS", "INDUSINDBK.NS", "FEDERALBNK.NS", "IDFCFIRSTB.NS"]},
    "^CNXIT": {"name": "Information Tech", "stocks": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS", "LTIM.NS", "PERSISTENT.NS", "COFORGE.NS"]},
    "^CNXAUTO": {"name": "Automotive", "stocks": ["M&M.NS", "TATAMOTORS.NS", "MARUTI.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", "HEROMOTOCO.NS", "TVSMOTOR.NS", "ASHOKLEY.NS"]},
    "^CNXPHARMA": {"name": "Pharma & Healthcare", "stocks": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "DIVISLAB.NS", "LUPIN.NS", "TORNTPHARM.NS", "ZYDUSLIFE.NS", "ALKEM.NS"]},
    "^CNXFMCG": {"name": "FMCG / Consumer", "stocks": ["ITC.NS", "HUL.NS", "NESTLEIND.NS", "BRITANNIA.NS", "TATACONSUM.NS", "VBL.NS", "GODREJCP.NS", "DABUR.NS", "MARICO.NS"]},
    "^CNXMETAL": {"name": "Metals & Mining", "stocks": ["TATASTEEL.NS", "HINDALCO.NS", "JSWSTEEL.NS", "VEDL.NS", "COALINDIA.NS", "JINDALSTEL.NS", "NMDC.NS"]},
    "^CNXREALTY": {"name": "Real Estate", "stocks": ["DLF.NS", "GODREJPROP.NS", "LODHA.NS", "OBEROIRLTY.NS", "PHOENIXLTD.NS", "PRESTIGE.NS"]},
    "^CNXENERGY": {"name": "Energy & Power", "stocks": ["RELIANCE.NS", "NTPC.NS", "ONGC.NS", "POWERGRID.NS", "BPCL.NS", "IOC.NS", "TATAPOWER.NS"]},
    "^CNXINFRA": {"name": "Infrastructure", "stocks": ["LT.NS", "GMRINFRA.NS", "IRCTC.NS", "CONCOR.NS", "SIEMENS.NS", "ABB.NS"]}
}

# =========================================================
# AGENT 1 & 2: DYNAMIC SECTOR & STOCK MOMENTUM SCANNER
# =========================================================
@st.cache_data(ttl=3600)
def get_momentum_rankings(lookback="3mo"):
    """Finds the Top 5 Sectors, then the Top 5 Stocks in each sector."""
    # 1. Rank Sectors
    indices = list(SECTOR_MAP.keys())
    hist = yf.download(indices, period=lookback, progress=False)['Close']
    
    if hist.empty:
        return {}
        
    sector_returns = ((hist.iloc[-1] - hist.iloc[0]) / hist.iloc[0]) * 100
    top5_indices = sector_returns.nlargest(5).index.tolist()
    
    top5_structure = {}
    
    # 2. Rank Stocks inside those Top 5 Sectors
    for idx in top5_indices:
        sec_name = SECTOR_MAP[idx]["name"]
        stocks = SECTOR_MAP[idx]["stocks"]
        
        stock_hist = yf.download(stocks, period=lookback, progress=False)['Close']
        if not stock_hist.empty:
            stock_returns = ((stock_hist.iloc[-1] - stock_hist.iloc[0]) / stock_hist.iloc[0]) * 100
            # Get Top 5 stocks per sector
            best_5_stocks = stock_returns.nlargest(5).index.tolist()
            top5_structure[sec_name] = best_5_stocks
            
    return top5_structure

# =========================================================
# AGENT 3: 10-PILLAR FUNDAMENTAL EXTRACTOR (YFINANCE)
# =========================================================
def extract_fundamentals(ticker, sector_name):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Core Metrics
        pe = info.get('trailingPE', np.nan)
        roe = info.get('returnOnEquity', np.nan)
        debt_to_equity = info.get('debtToEquity', np.nan)
        op_margin = info.get('operatingMargins', np.nan)
        current_ratio = info.get('currentRatio', np.nan)
        div_yield = info.get('dividendYield', np.nan)
        
        # Format metrics safely
        roe_pct = round(roe * 100, 2) if pd.notnull(roe) else 0.0
        de_ratio = round(debt_to_equity / 100, 2) if pd.notnull(debt_to_equity) else 0.0
        opm_pct = round(op_margin * 100, 2) if pd.notnull(op_margin) else 0.0
        
        # Execute 10-Pillar Rule Scoring (0 to 10 points)
        score = 0
        checks = []
        
        if roe_pct >= 15: score += 2; checks.append("ROE > 15%")
        if de_ratio <= 0.5: score += 2; checks.append("Debt/Equity < 0.5")
        elif de_ratio <= 1.0: score += 1; checks.append("Debt/Equity < 1.0")
        if opm_pct >= 10: score += 2; checks.append("Operating Margin > 10%")
        if pd.notnull(current_ratio) and current_ratio >= 1.5: score += 1; checks.append("Current Ratio > 1.5")
        if pd.notnull(pe) and 0 < pe <= 40: score += 1; checks.append("Reasonable P/E (<40)")
        if pd.notnull(div_yield) and div_yield > 0.01: score += 1; checks.append("Pays Dividends")
        
        return {
            "Symbol": ticker.replace(".NS", ""),
            "Sector": sector_name,
            "P/E Ratio": round(pe, 2) if pd.notnull(pe) else "N/A",
            "ROE (%)": roe_pct,
            "Debt/Equity": de_ratio,
            "Oper. Margin (%)": opm_pct,
            "Score (/10)": score,
            "Strengths": ", ".join(checks)
        }
    except Exception:
        return None

# =========================================================
# AGENT 4: AI LONG-TERM COMMITTEE
# =========================================================
def run_long_term_critique(stock_data):
    if not ai_model:
        return "AI Critic offline."
        
    prompt = f"""
    You are an elite Indian Stock Market Long-Term Value Investing Committee analyzing {stock_data['Symbol']} (Sector: {stock_data['Sector']}).
    
    Company Financial Metrics:
    - P/E Ratio: {stock_data['P/E Ratio']}
    - ROE: {stock_data['ROE (%)']}%
    - Debt-to-Equity: {stock_data['Debt/Equity']}
    - Operating Margin: {stock_data['Oper. Margin (%)']}%
    
    Evaluate this stock against strict long-term investment pillars:
    1. **Business Quality & Pricing Power**
    2. **Balance Sheet Strength & ROE Quality** (Is the ROE driven by debt or pure margins?)
    3. **Valuation & Margin of Safety** (Does the P/E justify long-term holding?)
    4. **Final Verdict**: STRONG BUY, HOLD/ACCUMULATE, or AVOID. Provide a 1-sentence justification.
    """
    try:
        response = ai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Committee review failed: {e}"

# =========================================================
# DASHBOARD INTERFACE
# =========================================================
lookback_period = st.sidebar.selectbox("Momentum Scan Period", ["1mo", "3mo", "6mo"], index=1)

if st.button(f"🚀 Run Automated 25-Stock Long-Term Pipeline ({lookback_period})"):
    
    # 1. SCAN FOR TOP SECTORS AND STOCKS
    with st.spinner("Agent 1 & 2: Scanning National Stock Exchange for Top 5 Sectors & 25 Stocks..."):
        top5_structure = get_momentum_rankings(lookback=lookback_period)
        
    if not top5_structure:
        st.error("Failed to retrieve market data from Yahoo Finance. Try again in a moment.")
    else:
        st.success(f"🎯 Successfully identified Top 5 Sectors: {', '.join(top5_structure.keys())}")
        
        # 2. EXTRACT FUNDAMENTALS
        with st.spinner("Agent 3: Extracting Deep Fundamentals (ROE, Debt, Margins) for all 25 stocks..."):
            all_records = []
            for sector, stocks in top5_structure.items():
                for ticker in stocks:
                    data = extract_fundamentals(ticker, sector)
                    if data:
                        all_records.append(data)
                    time.sleep(0.5) # Prevent Yahoo Finance rate limits
            
            df_fundamentals = pd.DataFrame(all_records)
            
            # Sort by our 10-Pillar Rule Score
            df_fundamentals = df_fundamentals.sort_values(by="Score (/10)", ascending=False).reset_index(drop=True)
            
        st.subheader("📊 Fundamental Screener: The 25 Best Performing Stocks")
        st.dataframe(df_fundamentals, use_container_width=True)

        # 3. AI COMMITTEE REVIEW FOR THE TOP SCORING STOCKS
        st.subheader("🏛️ Agent 4: AI Committee Deep-Dive (Top 5 Fundamentally Strongest Stocks)")
        st.info("The AI is writing a detailed thesis on the 5 stocks that scored highest on your Long-Term Checklist.")
        
        with st.spinner("AI agents reviewing fundamental moats and valuations..."):
            # Only run AI on the Top 5 absolute best stocks to keep the app fast
            top_5_fundamental_stocks = df_fundamentals.head(5).to_dict('records')
            
            for candidate in top_5_fundamental_stocks:
                critique = run_long_term_critique(candidate)
                with st.expander(f"📌 {candidate['Symbol']} ({candidate['Sector']}) — Score: {candidate['Score (/10)']}/10 | P/E: {candidate['P/E Ratio']} | ROE: {candidate['ROE (%)']}%", expanded=False):
                    st.markdown(critique)
