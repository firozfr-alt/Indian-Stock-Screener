import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

st.set_page_config(page_title="Indian Market Long-Term Screener", layout="wide")

st.title("📈 Indian Stock Market: Long-Term Screener")
st.markdown("A free, open-source dashboard extracting live data directly from **Screener.in**")

# Screener.in uses standard NSE symbols (No .NS required)
UNIVERSES = {
    "Large Cap": ["RELIANCE", "TCS", "HDFCBANK", "INFY", "HUL"],
    "Mid Cap": ["POLYCAB", "TRENT", "DIXON", "IDFCFIRSTB"],
    "Small & Micro Cap": ["SUZLON", "IREDA", "RVNL", "RENUKA", "YESBANK"]
}

selected_cap = st.selectbox("Select Market Cap Universe to Screen", list(UNIVERSES.keys()))
tickers = UNIVERSES[selected_cap]

# Cache the data for 1 hour so you don't scrape the same stock multiple times
@st.cache_data(ttl=3600) 
def fetch_screener_data(symbol):
    url = f"https://www.screener.in/company/{symbol}/consolidated/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers, timeout=10)
    
    # Fallback to standalone if the company doesn't have a consolidated page
    if response.status_code == 404:
        url = f"https://www.screener.in/company/{symbol}/"
        response = requests.get(url, headers=headers, timeout=10)
        
    if response.status_code != 200:
        return None
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    metrics = {
        "Ticker": symbol,
        "Price (₹)": 0,
        "Market Cap (Cr)": 0,
        "ROE (%)": 0,
        "Debt-to-Equity": 0,
        "P/E Ratio": 0
    }
    
    # Helper function to find specific numbers on the Screener page
    def get_value(search_term):
        try:
            spans = soup.find_all('span', class_='name')
            for span in spans:
                if search_term.lower() in span.text.lower():
                    parent = span.find_parent('li')
                    if parent:
                        number_span = parent.find('span', class_='number')
                        if number_span:
                            return float(number_span.text.replace(',', ''))
        except:
            pass
        return 0

    # Extract precise Indian market metrics
    metrics["Price (₹)"] = get_value("Current Price")
    metrics["Market Cap (Cr)"] = get_value("Market Cap")
    metrics["ROE (%)"] = get_value("ROE")
    metrics["Debt-to-Equity"] = get_value("Debt to equity")
    metrics["P/E Ratio"] = get_value("Stock P/E")
    
    return metrics

if st.button("🚀 Run Screener"):
    with st.spinner("Fetching data directly from Screener.in..."):
        results = []
        progress_bar = st.progress(0)
        
        for i, ticker in enumerate(tickers):
            data = fetch_screener_data(ticker)
            
            # Check if we successfully pulled market cap to verify data
            if data and data["Market Cap (Cr)"] > 0:
                results.append(data)
            
            # Wait 1 second between stocks so Screener.in doesn't block us
            time.sleep(1) 
            progress_bar.progress((i + 1) / len(tickers))
                
        df = pd.DataFrame(results)
        
        st.subheader(f"Raw Data: {selected_cap}")
        st.dataframe(df)
        
        st.subheader("✅ Passed Long-Term Criteria")
        
        if df.empty:
            st.error("⚠️ Failed to fetch data. Screener.in might be temporarily unavailable.")
        else:
            # Apply Long-Term Strategy Filters
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
