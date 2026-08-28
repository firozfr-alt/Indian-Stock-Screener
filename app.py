import streamlit as st
import pandas as pd
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from fpdf import FPDF
import google.generativeai as genai

st.set_page_config(page_title="Indian Market AI Multi-Agent Screener", layout="wide")
st.title("🤖 Indian Stock Market: AI Multi-Agent Screener")

# Initialize Gemini AI if the API key is present in Streamlit Secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None
    st.warning("⚠️ AI Agent is offline: GEMINI_API_KEY not found in Streamlit Secrets. The rest of the dashboard will still work normally.")

SECTOR_MAP = {
    "^NSEBANK": {"name": "Banking", "stocks": ["HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK"]},
    "^CNXIT": {"name": "Information Tech", "stocks": ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM"]},
    "^CNXAUTO": {"name": "Automotive", "stocks": ["M&M", "TATAMOTORS", "MARUTI", "BAJAJ-AUTO", "EICHERMOT"]},
    "^CNXPHARMA": {"name": "Pharma & Healthcare", "stocks": ["SUNPHARMA", "CIPLA", "DRREDDY", "DIVISLAB", "LUPIN"]}
}

@st.cache_data(ttl=3600)
def fetch_screener_deep_fundamentals(symbol):
    url = f"https://www.screener.in/company/{symbol}/consolidated/"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # NEW BUG FIX: Try-Except block to prevent ConnectionErrors from crashing the app
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 404:
            url = f"https://www.screener.in/company/{symbol}/"
            response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
    except requests.exceptions.RequestException:
        # If the connection drops, fail gracefully instead of crashing
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    
    def get_ratio(name_str):
        try:
            for span in soup.find_all('span', class_='name'):
                if name_str.lower() in span.text.lower():
                    parent = span.find_parent('li')
                    if parent:
                        num = parent.find('span', class_='number')
                        if num: return float(num.text.replace(',', ''))
        except: pass
        return 0.0

    data = {
        "Ticker": symbol,
        "Price (₹)": get_ratio("Current Price"),
        "Market Cap (Cr)": get_ratio("Market Cap"),
        "P/E Ratio": get_ratio("Stock P/E"),
        "ROCE (%)": get_ratio("ROCE"),
        "ROE (%)": get_ratio("ROE"),
        "Debt-to-Equity": get_ratio("Debt to equity"),
        "5Y Profit CAGR (%)": get_ratio("Compounded Profit Growth"),
    }
    
    score = 0
    if data["ROE (%)"] >= 15: score += 1
    if data["ROCE (%)"] >= 15: score += 1
    if data["Debt-to-Equity"] <= 0.5: score += 2
    data["Score (/10)"] = score
    
    if score >= 3: data["Verdict"] = "Quality Compounder"
    else: data["Verdict"] = "High Risk"
        
    return data

def run_ai_analysis(ticker, data):
    if not ai_model: return "AI Analyst offline."
    
    prompt = f"""
    Act as an elite Indian Stock Market fundamental analyst. Review this data for {ticker}:
    ROE: {data['ROE (%)']}%, ROCE: {data['ROCE (%)']}%, Debt/Equity: {data['Debt-to-Equity']}, P/E: {data['P/E Ratio']}, 5Y Profit CAGR: {data['5Y Profit CAGR (%)']}%.
    Write a strict, professional 3-sentence summary of the company's long-term viability. Mention if the valuation (P/E) is justified by the growth/ROE. Highlight any red flags.
    """
    try:
        response = ai_model.generate_content(prompt)
        return response.text.replace('\n', ' ')
    except:
        return "AI generated an error during analysis."

class PDFReport(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 14)
        self.cell(0, 8, "AI Multi-Agent Fundamental Report", ln=True, align="C")
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
            pdf.cell(0, 6, f"{row['Ticker']} | Score: {row['Score (/10)']}/10", ln=True)
            pdf.set_font("helvetica", "", 8)
            stats = f"Price: INR {row['Price (₹)']} | P/E: {row['P/E Ratio']} | ROE: {row['ROE (%)']}% | Debt/Eq: {row['Debt-to-Equity']}"
            pdf.cell(0, 4, stats, ln=True)
            
            # Print AI Agent Verdict in PDF
            pdf.set_font("helvetica", "I", 8)
            pdf.multi_cell(0, 4, f"🤖 AI Analyst Verdict: {row.get('AI_Analysis', 'No AI Analysis generated.')}")
            pdf.ln(3)
    return bytes(pdf.output())

if st.button("🚀 Run AI Pipeline"):
    indices = list(SECTOR_MAP.keys())
    with st.spinner("Agent 1: Scanning Sectors..."):
        hist = yf.download(indices, period="1mo", progress=False)['Close']
        returns = ((hist.iloc[-1] - hist.iloc[0]) / hist.iloc[0]) * 100
        top2_indices = returns.nlargest(2) # Keeping it to Top 2 to speed up the AI
        top2_sectors = {idx: SECTOR_MAP[idx] for idx in top2_indices.index}
        
    all_results = {}
    for idx, sec_info in top2_sectors.items():
        sec_name = sec_info["name"]
        raw_stocks = sec_info["stocks"]
        
        with st.spinner(f"Agent 2 & 3: Processing Fundamentals & AI Analysis for {sec_name}..."):
            yf_symbols = [s + ".NS" for s in raw_stocks]
            stock_hist = yf.download(yf_symbols, period="1mo", progress=False)['Close']
            stock_returns = ((stock_hist.iloc[-1] - stock_hist.iloc[0]) / stock_hist.iloc[0]) * 100
            top2_stocks = [s.replace(".NS", "") for s in stock_returns.nlargest(2).index.tolist()]
            
            sector_fund_data = []
            for ticker in top2_stocks:
                fund_data = fetch_screener_deep_fundamentals(ticker)
                if fund_data:
                    # RUN AI AGENT HERE
                    fund_data["AI_Analysis"] = run_ai_analysis(ticker, fund_data)
                    sector_fund_data.append(fund_data)
                time.sleep(1.5) 
                
            df_sec = pd.DataFrame(sector_fund_data)
            all_results[sec_name] = df_sec
            st.subheader(f"📊 {sec_name}")
            st.dataframe(df_sec.drop(columns=["AI_Analysis"], errors='ignore'), use_container_width=True)
            for _, row in df_sec.iterrows():
                st.info(f"**🤖 AI Analyst ({row['Ticker']}):** {row['AI_Analysis']}")
            
    pdf_bytes = generate_pdf(all_results)
    st.download_button(label="📄 Download AI Report (PDF)", data=pdf_bytes, file_name="AI_Sector_Report.pdf", mime="application/pdf")
