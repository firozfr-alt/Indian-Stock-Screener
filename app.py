import streamlit as st
from yahooquery import Ticker
import pandas as pd

st.set_page_config(page_title="Indian Market Long-Term Screener", layout="wide")

st.title("📈 Indian Stock Market: Long-Term Screener")
st.markdown("A free, open-source dashboard to screen NSE stocks based on Quality and Debt metrics.")

UNIVERSES = {
    "Large Cap": ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HUL.NS"],
    "Mid Cap": ["POLYCAB.NS", "TRENT.NS", "DIXON.NS", "IDFCFIRSTB.NS"],
    "Small & Micro Cap": ["SUZLON.NS", "IREDA.NS", "RVNL.NS", "RENUKA.NS", "YESBANK.NS"]
}

selected_cap = st.selectbox("Select Market Cap Universe to Screen", list(UNIVERSES.keys()))
tickers_list = UNIVERSES[selected_cap]

if st.button("🚀 Run Screener"):
    with st.spinner("Bypassing cloud blocks using Yahoo backend API..."):
        
        # yahooquery fetches all tickers instantly in one batch
        tickers = Ticker(tickers_list)
        
        # Pull backend dictionaries
        fin_data = tickers.financial_data
        summary_data = tickers.summary_detail
        
        results = []
        for symbol in tickers_list:
            try:
                # Check if Yahoo successfully returned data for this symbol
                if isinstance(fin_data, dict) and symbol in fin_data and isinstance(fin_data[symbol], dict):
                    f_data = fin_data[symbol]
                    s_data = summary_data.get(symbol, {})
                    
                    # Extract metrics safely from the API dictionaries
                    price = s_data.get("regularMarketPrice", 0) or s_data.get("previousClose", 0)
                    market_cap = s_data.get("marketCap", 0) / 10000000
                    roe = (f_data.get("returnOnEquity", 0) or 0) * 100
                    debt_equity = (f_data.get("debtToEquity", 0) or 0) / 100
                    pe_ratio = s_data.get("trailingPE", 0) or 0
                    
                    results.append({
                        "Ticker": symbol.replace(".NS", ""),
                        "Price (₹)": round(price, 2),
                        "Market Cap (Cr)": round(market_cap, 2),
                        "ROE (%)": round(roe, 2),
                        "Debt-to-Equity": round(debt_equity, 2),
                        "P/E Ratio": round(pe_ratio, 2)
                    })
            except Exception as e:
                pass
                
        df = pd.DataFrame(results)
        
        st.subheader(f"Raw Data: {selected_cap}")
        st.dataframe(df)
        
        # Apply Long-Term Strategy Filters
        st.subheader("✅ Passed Long-Term Criteria")
        
        if df.empty:
            st.error("⚠️ Failed to fetch data. Ensure ticker symbols are correct.")
        else:
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
