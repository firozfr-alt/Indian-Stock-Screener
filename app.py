import streamlit as st
import pandas as pd
import yfinance as yf
import google.generativeai as genai
from datetime import datetime, timedelta

st.set_page_config(page_title="AI Market Agents", layout="wide")
st.title("🤖 AI Multi-Agent Indian Stock Screener")

# ==========================================
# AGENT INITIALIZATION (GEMINI API)
# ==========================================
# Securely load the API key from Streamlit Secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
    st.success("✅ AI Agent Online and Connected.")
else:
    ai_model = None
    st.error("🚨 AI Offline: GEMINI_API_KEY not found in Streamlit Secrets.")

# Core Indian Market Universe (Yahoo Finance uses .NS for NSE)
TICKERS = {
    "Reliance": "RELIANCE.NS", "TCS": "TCS.NS", "HDFC Bank": "HDFCBANK.NS", 
    "Infosys": "INFY.NS", "ICICI Bank": "ICICIBANK.NS", "ITC": "ITC.NS", 
    "L&T": "LT.NS", "SBI": "SBIN.NS", "Bharti Airtel": "BHARTIARTL.NS"
}

# ==========================================
# AGENT 1 & 2: DATA GATHERING (YFINANCE)
# ==========================================
@st.cache_data(ttl=3600)
def fetch_stock_data(ticker_symbol):
    """Fetches stable data using yfinance (immune to Cloudflare blocks)"""
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        hist = stock.history(period="6mo")
        
        if hist.empty: return None
        
        current_price = hist['Close'].iloc[-1]
        price_6m_ago = hist['Close'].iloc[0]
        momentum_6m = ((current_price - price_6m_ago) / price_6m_ago) * 100

        return {
            "Symbol": ticker_symbol,
            "Price": round(current_price, 2),
            "Momentum (6M)": round(momentum_6m, 2),
            "P/E Ratio": info.get('trailingPE', 'N/A'),
            "ROE (%)": round(info.get('returnOnEquity', 0) * 100, 2) if info.get('returnOnEquity') else 'N/A',
            "Debt-to-Equity": info.get('debtToEquity', 'N/A')
        }
    except:
        return None

# ==========================================
# AGENT 3: AI CHIEF STRATEGIST
# ==========================================
def generate_ai_verdict(stock_data, strategy_type):
    """Feeds the financial data to Gemini to write an expert verdict"""
    if not ai_model: return "AI is offline."
    
    prompt = f"""
    Act as an elite Indian Stock Market analyst. Review this data for {stock_data['Symbol']}:
    - Current Price: ₹{stock_data['Price']}
    - 6-Month Momentum: {stock_data['Momentum (6M)']}%
    - P/E Ratio: {stock_data['P/E Ratio']}
    - ROE: {stock_data['ROE (%)']}%
    - Debt-to-Equity: {stock_data['Debt-to-Equity']}
    
    The user is looking for a {strategy_type} trade. 
    Write a strict, professional 3-sentence summary of the company's viability for this strategy. 
    Highlight any major red flags based on these specific numbers. End with a clear VERDICT (Buy, Hold, or Avoid).
    """
    
    try:
        response = ai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Analysis failed: {e}"

# ==========================================
# DASHBOARD UI
# ==========================================
strategy = st.radio("Select AI Strategy Focus:", ["Long-Term Value (Q-GARP)", "Medium-Term Swing Trading (Momentum)"])

if st.button("🚀 Run AI Analysis Pipeline"):
    with st.spinner("Agents 1 & 2 gathering market data..."):
        market_data = []
        for name, symbol in TICKERS.items():
            data = fetch_stock_data(symbol)
            if data: market_data.append(data)
            
        df = pd.DataFrame(market_data)
        st.dataframe(df, use_container_width=True)
        
    with st.spinner("Agent 3 (Gemini) writing strategic verdicts..."):
        # We will run the AI on the top 2 stocks to keep it fast
        if strategy == "Medium-Term Swing Trading (Momentum)":
            top_stocks = df.nlargest(2, 'Momentum (6M)').to_dict('records')
            st.subheader("🔥 AI Verdicts: Top Momentum Breakouts")
        else:
            # Filter for Long Term: Needs numeric ROE
            df_numeric_roe = df[pd.to_numeric(df['ROE (%)'], errors='coerce').notnull()]
            top_stocks = df_numeric_roe.nlargest(2, 'ROE (%)').to_dict('records')
            st.subheader("🏦 AI Verdicts: Top Quality Compounders")
            
        for stock in top_stocks:
            verdict = generate_ai_verdict(stock, strategy)
            with st.expander(f"🤖 AI Analyst Verdict: {stock['Symbol']}", expanded=True):
                st.write(verdict)
