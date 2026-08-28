import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from fpdf import FPDF

st.set_page_config(page_title="Indian Market 10-Pillar Multi-Agent Screener", layout="wide")
st.title("🏛️ Indian Stock Market: 10-Pillar Multi-Agent Screener")
st.markdown("Automated 3-Agent pipeline analyzing **Top 4 Sectors**, **Top 4 Stocks per Sector (16 total)**, and executing full **10-Pillar Fundamental Analysis** with PDF export.")

SECTOR_MAP = {
    "^NSEBANK": {"name": "Banking", "stocks": ["HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK", "INDUSINDBK"]},
    "^CNXIT": {"name": "Information Tech", "stocks": ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM", "LTIM"]},
    "^CNXAUTO": {"name": "Automotive", "stocks": ["M&M", "TATAMOTORS", "MARUTI", "BAJAJ-AUTO", "EICHERMOT", "HEROMOTOCO"]},
    "^CNXPHARMA": {"name": "Pharma & Healthcare", "stocks": ["SUNPHARMA", "CIPLA", "DRREDDY", "DIVISLAB", "LUPIN", "TORNTPHARM"]},
    "^CNXFMCG": {"name": "FMCG / Consumer", "stocks": ["ITC", "HUL", "NESTLEIND", "BRITANNIA", "TATACONSUM", "VBL"]},
    "^CNXMETAL": {"name": "Metals & Mining", "stocks": ["TATASTEEL", "HINDALCO", "JSWSTEEL", "VEDL", "COALINDIA", "JINDALSTEL"]},
    "^CNXREALTY": {"name": "Real Estate", "stocks": ["DLF", "GODREJPROP", "LODHA", "OBEROIRLTY", "PHOENIXLTD"]},
    "^CNXENERGY": {"name": "Energy & Power", "stocks": ["RELIANCE", "NTPC", "ONGC", "POWERGRID", "BPCL", "IOC"]}
}

@st.cache_data(ttl=3600)
def fetch_screener_deep_fundamentals(symbol):
    url = f"https://www.screener.in/company/{symbol}/consolidated/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # --- BUG FIX: Added a safety net for connection drops ---
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 404:
            url = f"https://www.screener.in/company/{symbol}/"
            response = requests.get(url, headers=headers, timeout=10)
            
        if response.status_code != 200:
            return None
    except Exception as e:
        # If Screener.in drops the connection, gracefully fail and skip the stock
        return None
    # ---------------------------------------------------------

    soup = BeautifulSoup(response.text, 'html.parser')
    
    def get_ratio(name_str):
        try:
            for span in soup.find_all('span', class_='name'):
                if name_str.lower() in span.text.lower():
                    parent = span.find_parent('li')
                    if parent:
                        num = parent.find('span', class_='number')
                        if num:
                            return float(num.text.replace(',', ''))
        except:
            pass
        return 0.0

    def get_growth(table_title, period="5 Years:"):
        try:
            tables = soup.find_all('table', class_='ranges-table')
            for t in tables:
                th = t.find('th')
                if th and table_title.lower() in th.text.lower():
                    for tr in t.find_all('tr'):
                        tds = tr.find_all('td')
                        if len(tds) == 2 and period.lower() in tds[0].text.lower():
                            val_str = tds[1].text.replace('%', '').replace(',', '').strip()
                            return float(val_str)
        except:
            pass
        return 0.0

    data = {
        "Ticker": symbol,
        "Price (₹)": get_ratio("Current Price"),
        "Market Cap (Cr)": get_ratio("Market Cap"),
        "P/E Ratio": get_ratio("Stock P/E"),
        "ROCE (%)": get_ratio("ROCE"),
        "ROE (%)": get_ratio("ROE"),
        "Debt-to-Equity": get_ratio("Debt to equity"),
        "Interest Coverage": get_ratio("Interest Coverage"),
        "Promoter Holding (%)": get_ratio("Promoter holding"),
        "Pledged (%)": get_ratio("Pledged percentage"),
        "5Y Sales CAGR (%)": get_growth("Compounded Sales Growth", "5 Years:"),
        "5Y Profit CAGR (%)": get_growth("Compounded Profit Growth", "5 Years:"),
        "Dividend Yield (%)": get_ratio("Dividend Yield"),
    }
    
    score = 0
    checks = []

    if data["ROE (%)"] >= 15: score += 1; checks.append("ROE >= 15%")
    if data["ROCE (%)"] >= 15: score += 1; checks.append("ROCE >= 15%")
    if data["5Y Sales CAGR (%)"] >= 10: score += 1; checks.append("5Y Sales >= 10%")
    if data["5Y Profit CAGR (%)"] >= 12: score += 1; checks.append("5Y Profit >= 12%")
    if data["Debt-to-Equity"] <= 0.5: score += 2; checks.append("D/E <= 0.5")
    elif data["Debt-to-Equity"] <= 1.0: score += 1; checks.append("D/E <= 1.0")
    if data["Interest Coverage"] >= 3.0 or data["Interest Coverage"] == 0.0: score += 1; checks.append("Int Cov >= 3x")
    if data["Promoter Holding (%)"] >= 50: score += 1; checks.append("Promoter >= 50%")
    if data["Pledged (%)"] <= 5.0: score += 1; checks.append("Low Pledging")
    if 0 < data["P/E Ratio"] <= 35: score += 1; checks.append("Reasonable P/E")

    data["Score (/10)"] = score
    data["Passed Checks"] = ", ".join(checks)
    
    if score >= 8: data["Verdict"] = "STRONG COMPOUNDER"
    elif score >= 6: data["Verdict"] = "MODERATE QUALITY"
    else: data["Verdict"] = "WATCHLIST / HIGH RISK"
        
    return data

class PDFReport(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 14)
        self.cell(0, 8, "Indian Stock Market: 10-Pillar Screener", ln=True, align="C")
        self.set_font("helvetica", "I", 9)
        self.cell(0, 5, f"Generated on: {datetime.now().strftime('%d %b %Y, %H:%M IST')}", ln=True, align="C")
        self.ln(4)

def generate_pdf(all_sector_results):
    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    
    for sector_name, df_stocks in all_sector_results.items():
        pdf.set_font("helvetica", "B", 12)
        pdf.set_fill_color(230, 235, 245)
        pdf.cell(0, 7, f"Sector: {sector_name}", ln=True, fill=True)
        pdf.ln(2)
        
        for _, row in df_stocks.iterrows():
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(0, 6, f"{row['Ticker']} | Score: {row['Score (/10)']}/10 | Verdict: {row['Verdict']}", ln=True)
            pdf.set_font("helvetica", "", 8)
            pdf.cell(0, 4, f"Price: INR {row['Price (₹)']} | MCap: {row['Market Cap (Cr)']} Cr | P/E: {row['P/E Ratio']}", ln=True)
            pdf.cell(0, 4, f"ROE: {row['ROE (%)']}% | ROCE: {row['ROCE (%)']}% | Debt/Equity: {row['Debt-to-Equity']}", ln=True)
            pdf.set_font("helvetica", "I", 8)
            pdf.multi_cell(0, 4, f"Strengths: {row['Passed Checks']}")
            pdf.ln(3)
        pdf.ln(3)
    return bytes(pdf.output())

lookback = st.selectbox("Sector Momentum Lookback Period", ["1mo", "3mo", "6mo"], index=0)

if st.button("🚀 Run 3-Agent 10-Pillar Pipeline"):
    with st.spinner("Agent 1: Scanning Indian Sectoral Indices..."):
        indices = list(SECTOR_MAP.keys())
        hist = yf.download(indices, period=lookback, progress=False)['Close']
        returns = ((hist.iloc[-1] - hist.iloc[0]) / hist.iloc[0]) * 100
        
        top4_indices = returns.nlargest(4)
        top4_sectors = {idx: SECTOR_MAP[idx] for idx in top4_indices.index}
        
        st.subheader("🏆 Agent 1: Top 4 Outperforming Sectors")
        sec_df = pd.DataFrame({
            "Sector Name": [SECTOR_MAP[idx]["name"] for idx in top4_indices.index],
            f"Return ({lookback}) %": [round(val, 2) for val in top4_indices.values]
        })
        st.dataframe(sec_df, use_container_width=True)

    all_results = {}
    progress_bar = st.progress(0)
    
    for i, (idx, sec_info) in enumerate(top4_sectors.items()):
        sec_name = sec_info["name"]
        raw_stocks = sec_info["stocks"]
        
        with st.spinner(f"Agent 2 & 3: Processing {sec_name}..."):
            yf_symbols = [s + ".NS" for s in raw_stocks]
            stock_hist = yf.download(yf_symbols, period=lookback, progress=False)['Close']
            stock_returns = ((stock_hist.iloc[-1] - stock_hist.iloc[0]) / stock_hist.iloc[0]) * 100
            
            top4_stocks = [s.replace(".NS", "") for s in stock_returns.nlargest(4).index.tolist()]
            
            sector_fund_data = []
            for ticker in top4_stocks:
                fund_data = fetch_screener_deep_fundamentals(ticker)
                if fund_data:
                    sector_fund_data.append(fund_data)
                time.sleep(1) # Protect against blocks
                
            if sector_fund_data:
                df_sec = pd.DataFrame(sector_fund_data)
                all_results[sec_name] = df_sec
                st.subheader(f"📊 {sec_name}: Top 4 Stocks Fundamentals")
                st.dataframe(df_sec.drop(columns=["Passed Checks"]), use_container_width=True)
            
        progress_bar.progress((i + 1) / 4)
        
    if all_results:
        pdf_bytes = generate_pdf(all_results)
        st.success("✅ Complete 16-Stock 10-Pillar Analysis Complete!")
        st.download_button(label="📄 Download 16-Stock PDF Report", data=pdf_bytes, file_name="Screener_Report.pdf", mime="application/pdf")
