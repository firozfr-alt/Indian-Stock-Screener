import streamlit as st
import yfinance as yf
import pandas as pd
import time

st.set_page_config(page_title="Indian Market Long-Term Screener", layout="wide")

st.title("📈 Indian Stock Market: Long-Term Screener")
st.markdown("A free, open-source dashboard to screen NSE stocks based on Quality and Debt metrics.")

# Sample universes (In a production app, you would load a CSV of all 2000+ NSE tickers)
UNIVERSES = {
    "Large Cap": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HUL.NS"],
    "Mid Cap": ["POLYCAB.NS", "TRENT.NS", "DIXON.NS", "IDFCFIRSTB.NS"],
    "Small & Micro Cap": ["SUZLON.NS", "IREDA.NS", "RVNL.NS", "RENUKA.NS", "YESBANK.NS"]
}

selected_cap = st.selectbox("Select Market Cap Universe to Screen", list(UNIVERSES.keys()))
tickers = UNIVERSES[selected_cap]

if st.button("🚀 Run Screener"):
    with st.spinner("Fetching live fundamental data from Yahoo Finance..."):
        results = []
        # Create a progress bar
        progress_bar = st.progress(0)
        
        for i, ticker in enumerate(tickers):
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                # Extract fundamental metrics safely
                price = info.get("currentPrice", 0)
                market_cap = info.get("marketCap", 0) / 10000000 # Convert to Crores (₹)
                roe = info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else 0
                debt_equity = info.get("debtToEquity", 0) / 100 if info.get("debtToEquity") else 0
                pe_ratio = info.get("trailingPE", 0)
                
                results.append({
                    "Ticker": ticker.replace(".NS", ""),
                    "Price (₹)": price,
                    "Market Cap (Cr)": round(market_cap, 2),
                    "ROE (%)": round(roe, 2),
                    "Debt-to-Equity": round(debt_equity, 2),
                    "P/E Ratio": round(pe_ratio, 2)
                })
                # Polite rate limiting to avoid getting blocked by Yahoo
                time.sleep(0.5) 
            except Exception as e:
                continue
            
            progress_bar.progress((i + 1) / len(tickers))
                
        df = pd.DataFrame(results)
        
        st.subheader(f"Raw Data: {selected_cap}")
        st.dataframe(df)
        
        # Apply Long-Term Strategy Filters
        st.subheader("✅ Passed Long-Term Criteria")
        if selected_cap == "Large Cap":
            passed = df[(df["ROE (%)"] > 15) & (df["Debt-to-Equity"] < 0.5)]
            st.info("Rule: ROE > 15% and Debt-to-Equity < 0.5")
        elif selected_cap == "Mid Cap":
            passed = df[(df["ROE (%)"] > 15) & (df["Debt-to-Equity"] < 0.3)]
            st.info("Rule: ROE > 15% and Debt-to-Equity < 0.3")
        else:
            passed = df[df["Debt-to-Equity"] < 0.1]
            st.info("Rule: Ultra-low debt (Debt-to-Equity < 0.1) for survival")
            
        if not passed.empty:
            st.success(f"Found {len(passed)} stocks meeting the criteria!")
            st.dataframe(passed)
        else:
            st.warning("No stocks passed the criteria in this run.")
            
st.caption("*Disclaimer: This tool is for educational research and does not constitute financial advice.*")