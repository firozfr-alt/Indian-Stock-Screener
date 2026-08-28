import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from fpdf import FPDF

st.set_page_config(page_title="Indian Market Screener Hub", layout="wide")
st.title("📈 Indian Stock Market: Advanced Screener Hub")

# Create two tabs so you can run both strategies
tab1, tab2 = st.tabs(["Strategy 1: Quality Solvency (Q-GARP)", "Strategy 2: Multi-Agent Sector Screener & PDF"])

# ==========================================
# TAB 1: YOUR FIRST STRATEGY (Screener.in)
# ==========================================
with tab1:
    st.markdown("Your original strategy filtering for ROE and Debt across Market Caps.")
    
    UNIVERSES = {
        "Large Cap": ["RELIANCE", "TCS", "HDFCBANK", "INFY", "HUL"],
        "Mid Cap": ["POLYCAB", "TRENT", "DIXON", "IDFCFIRSTB"],
        "Small & Micro Cap": ["SUZLON", "IREDA", "RVNL", "RENUKA", "YESBANK"]
    }

    selected_cap = st.selectbox("Select Market Cap Universe", list(UNIVERSES.keys()), key="tab1_cap")
    tickers = UNIVERSES[selected_cap]

    @st.cache_data(ttl=3600) 
    def fetch_screener_data(symbol):
        url = f"https://www.screener.in/company/{symbol}/consolidated/"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            url = f"https://www.screener.in/company/{symbol}/"
            response = requests.get(url, headers=headers, timeout=10)
            
        if response.status_code != 200: return None
        soup = BeautifulSoup(response.text, 'html.parser')
        
        metrics = {"Ticker": symbol, "Price (₹)": 0, "Market Cap (Cr)": 0, "ROE (%)": 0, "Debt-to-Equity": 0, "P/E Ratio": 0}
        
        def get_value(search_term):
            try:
                spans = soup.find_all('span', class_='name')
                for span in spans:
                    if search_term.lower() in span.text.lower():
                        parent = span.find_parent('li')
                        if parent:
                            num = parent.find('span', class_='number')
                            if num: return float(num.text.replace(',', ''))
            except: pass
            return 0

        metrics["Price (₹)"] = get_value("Current Price")
        metrics["Market Cap (Cr)"] = get_value("Market Cap")
        metrics["ROE (%)"] = get_value("ROE")
        metrics["Debt-to-Equity"] = get_value("Debt to equity")
        metrics["P/E Ratio"] = get_value("Stock P/E")
        return metrics

    if st.button("🚀 Run Strategy 1"):
        with st.spinner("Fetching data from Screener.in..."):
            results = [fetch_screener_data(t) for t in tickers if fetch_screener_data(t)]
            df = pd.DataFrame(results)
            st.dataframe(df)
            
            st.subheader("✅ Passed Criteria")
            if not df.empty:
                if selected_cap == "Large Cap": passed = df[(df["ROE (%)"] > 15) & (df["Debt-to-Equity"] < 0.5)]
                elif selected_cap == "Mid Cap": passed = df[(df["ROE (%)"] > 15) & (df["Debt-to-Equity"] < 0.3)]
                else: passed = df[df["Debt-to-Equity"] < 0.1]
                st.dataframe(passed)

# ==========================================
# TAB 2: MULTI-AGENT SECTOR STRATEGY & PDF
# ==========================================
with tab2:
    st.markdown("A 3-Agent pipeline that identifies the best sector, screens its top stocks, and generates a PDF report.")
    
    # 1. Define Sector Indices and their heavyweights
    SECTOR_STOCKS = {
        "^NSEBANK": ["HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK"],
        "^CNXIT": ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM"],
        "^CNXAUTO": ["M&M", "TATAMOTORS", "MARUTI", "BAJAJ-AUTO", "EICHERMOT"],
        "^CNXPHARMA": ["SUNPHARMA", "CIPLA", "DRREDDY", "DIVISLAB", "LUPIN"],
        "^CNXFMCG": ["ITC", "HUL", "NESTLEIND", "BRITANNIA", "TATACONSUM"],
        "^CNXMETAL": ["TATASTEEL", "HINDALCO", "JSWSTEEL", "VEDL", "COALINDIA"]
    }
    SECTOR_NAMES = {
        "^NSEBANK": "Banking", "^CNXIT": "IT", "^CNXAUTO": "Automobiles", 
        "^CNXPHARMA": "Pharma", "^CNXFMCG": "FMCG", "^CNXMETAL": "Metals"
    }

    timeframe = st.radio("Select Investment Timeframe", ["Medium-Term (3-5 Years)", "Long-Term (5-10+ Years)"])

    def create_pdf_report(sector_name, timeframe, analyzed_data):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, "AI Multi-Agent Fundamental Report", ln=True, align="C")
        pdf.set_font("helvetica", "", 12)
        pdf.cell(0, 10, f"Winning Sector: {sector_name}", ln=True)
        pdf.cell(0, 10, f"Investment Horizon: {timeframe}", ln=True)
        pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d')}", ln=True)
        pdf.ln(5)
        
        for data in analyzed_data:
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 8, f"Stock: {data['Ticker']}", ln=True)
            pdf.set_font("helvetica", "", 10)
            pdf.cell(0, 6, f"Price: INR {data['Price (₹)']} | Market Cap: {data['Market Cap (Cr)']} Cr", ln=True)
            pdf.cell(0, 6, f"ROE: {data['ROE (%)']}% | Debt/Equity: {data['Debt-to-Equity']} | P/E: {data['P/E Ratio']}", ln=True)
            
            # Agent Verdict based on timeframe
            if timeframe == "Long-Term (5-10+ Years)":
                verdict = "STRONG BUY: High ROE (>15%) and low debt." if data['ROE (%)'] > 15 and data['Debt-to-Equity'] < 0.5 else "MONITOR: Fails strict long-term debt/efficiency rules."
            else:
                verdict = "ACCUMULATE: Acceptable metrics for medium-term." if data['ROE (%)'] > 12 and data['Debt-to-Equity'] < 0.8 else "AVOID: Weak fundamentals."
                
            pdf.set_font("helvetica", "I", 10)
            pdf.cell(0, 6, f"Agent Verdict: {verdict}", ln=True)
            pdf.ln(4)
            
        return bytes(pdf.output())

    if st.button("🤖 Launch AI Agents"):
        # --- AGENT 1: SECTOR PERFORMANCE ---
        with st.spinner("Agent 1: Analyzing 1-Month Sector Returns..."):
            indices = list(SECTOR_STOCKS.keys())
            # yf.download historical data is immune to cloud blocking
            hist_data = yf.download(indices, period="1mo", progress=False)['Close']
            returns = ((hist_data.iloc[-1] - hist_data.iloc[0]) / hist_data.iloc[0]) * 100
            best_index = returns.idxmax()
            best_sector_name = SECTOR_NAMES[best_index]
            st.success(f"**Agent 1 Verdict:** The strongest sector is **{best_sector_name}** with a 1-month return of {returns[best_index]:.2f}%.")

        # --- AGENT 2: STOCK SCREENER ---
        with st.spinner(f"Agent 2: Screening top stocks inside {best_sector_name}..."):
            stocks = SECTOR_STOCKS[best_index]
            yf_stocks = [s + ".NS" for s in stocks]
            stock_data = yf.download(yf_stocks, period="1mo", progress=False)['Close']
            stock_returns = ((stock_data.iloc[-1] - stock_data.iloc[0]) / stock_data.iloc[0]) * 100
            best_yf_stocks = stock_returns.nlargest(3).index.tolist()
            best_stocks_clean = [s.replace(".NS", "") for s in best_yf_stocks]
            st.success(f"**Agent 2 Verdict:** Identified top 3 momentum stocks: {', '.join(best_stocks_clean)}")

        # --- AGENT 3: FUNDAMENTAL ANALYSIS & PDF ---
        with st.spinner("Agent 3: Scraping fundamentals & generating PDF..."):
            analyzed_data = []
            for ticker in best_stocks_clean:
                data = fetch_screener_data(ticker)
                if data:
                    analyzed_data.append(data)
                time.sleep(1) # Polite scraping
                
            st.subheader(f"Fundamental Analysis: {best_sector_name}")
            st.dataframe(pd.DataFrame(analyzed_data))
            
            # Generate PDF in memory
            pdf_bytes = create_pdf_report(best_sector_name, timeframe, analyzed_data)
            
            st.success("**Agent 3 Verdict:** PDF Report Generated Successfully!")
            st.download_button(
                label="📄 Download Investment Report (PDF)",
                data=pdf_bytes,
                file_name=f"Investment_Report_{best_sector_name}.pdf",
                mime="application/pdf"
            )
