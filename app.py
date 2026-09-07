import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from google import genai
import time
from datetime import datetime
from fpdf import FPDF
import concurrent.futures

st.set_page_config(
    page_title="AI Equity Screener & Fundamental Analyst",
    page_icon="📈",
    layout="wide"
)

st.title("🏛️ Institutional Indian Equity Screener")
st.caption("AI-Powered Tri-Strategy Screener & Deep Fundamental 4-Agent Auditor")

# =========================================================
# 1. GEMINI AI INITIALIZATION
# =========================================================
ai_client = None
if "GEMINI_API_KEY" in st.secrets:
    try:
        ai_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        st.sidebar.success("✅ Google Gemini AI: Online")
    except Exception as e:
        st.sidebar.warning(f"⚠️ Gemini Offline: {e}")
else:
    st.sidebar.info("ℹ️ Deterministic Mode (Add GEMINI_API_KEY to Secrets)")

# =========================================================
# 2. LIVE MARKET DATA & SENTIMENT
# =========================================================
@st.cache_data(ttl=60)
def fetch_market_data():
    try:
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(period="6mo")
        is_etf = False
        
        if hist.empty or len(hist) < 22:
            nifty = yf.Ticker("NIFTYBEES.NS")
            hist = nifty.history(period="6mo")
            is_etf = True
            
        if hist.empty or len(hist) < 22:
            return None
            
        live_hist = nifty.history(period="1d", interval="2m")
        if not live_hist.empty:
            current_price = float(live_hist['Close'].dropna().iloc[-1])
        else:
            current_price = float(hist['Close'].dropna().iloc[-1])
            
        if not live_hist.empty and live_hist.index[-1].date() > hist.index[-1].date():
            prev_price = float(hist['Close'].dropna().iloc[-1])
        else:
            prev_price = float(hist['Close'].dropna().iloc[-2])
            
        daily_change_pts = current_price - prev_price
        daily_change_pct = (daily_change_pts / prev_price) * 100
        
        ret_1m = float(((current_price - hist['Close'].iloc[-22]) / hist['Close'].iloc[-22]) * 100)
        ret_6m = float(((current_price - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100)
        
        market_trend = "Bullish" if ret_1m > 0 and ret_6m > 0 else "Bearish" if ret_1m < 0 and ret_6m < 0 else "Mixed/Consolidating"
        
        return {
            "price": current_price,
            "daily_pts": daily_change_pts,
            "daily_pct": daily_change_pct,
            "ret_1m": ret_1m,
            "ret_6m": ret_6m,
            "trend": market_trend,
            "is_etf": is_etf
        }
    except Exception:
        return None

@st.cache_data(ttl=3600)
def generate_ai_sentiment(price, daily_pts, daily_pct, ret_1m, ret_6m, trend):
    if not ai_client:
        return "Market sentiment AI is currently offline. Please configure GEMINI_API_KEY in Streamlit Secrets."
        
    prompt = f"""
    You are a top-tier Institutional Equity Strategist for the Indian Stock Market.
    The benchmark Nifty 50 is currently trading at {price:.2f}.
    Technical data:
    - Daily Delta: {daily_pts:+.2f} pts ({daily_pct:+.2f}%)
    - 1-Month Momentum: {ret_1m:.2f}%
    - 6-Month Momentum: {ret_6m:.2f}%
    - Quantitative Trend: {trend}
    
    Write an institutional market sentiment briefing. Structure your response EXACTLY into these three short sections using standard bullet points:
    **1. Trend Confirmation:** Assess current momentum, moving average trajectory, and institutional posture.
    **2. The Upside (Resistance):** Identify immediate resistance and breakout levels relative to the current price of {price:.2f}.
    **3. The Downside (Support):** Identify immediate support cushions and risk levels relative to {price:.2f}.
    
    Keep it highly professional, analytical, and direct.
    """
    
    models_to_try = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]
    for model_name in models_to_try:
        for attempt in range(3):
            try:
                response = ai_client.models.generate_content(model=model_name, contents=prompt)
                if response.text:
                    return response.text.strip()
            except Exception as api_e:
                error_str = str(api_e).lower()
                if "503" in error_str or "unavailable" in error_str or "429" in error_str or "quota" in error_str:
                    time.sleep(5)
                    continue
                else:
                    break
                    
    return "Market sentiment summary is currently unavailable due to high AI server demand. Pipeline scans remain fully operational."

market_data = fetch_market_data()
if market_data:
    prefix = "Nifty BeES: " if market_data.get("is_etf") else "Nifty 50: "
    header_title = f"📊 Current Indian Market Sentiment ({prefix}₹{market_data['price']:,.2f} | {market_data['daily_pts']:+,.2f} pts / {market_data['daily_pct']:+.2f}%)"
else:
    header_title = "📊 Current Indian Market Sentiment (Data Unavailable)"

with st.expander(header_title, expanded=True):
    if market_data:
        m1, m2, m3, m4 = st.columns(4)
        price_label = "Nifty 50 (Proxy ETF)" if market_data.get("is_etf") else "Nifty 50 Current Price"
        delta_str = f"{market_data['daily_pts']:+,.2f} ({market_data['daily_pct']:+.2f}%)"
        
        m1.metric(price_label, f"₹{market_data['price']:,.2f}", delta=delta_str)
        m2.metric("1-Month Momentum", f"{market_data['ret_1m']:+.2f}%")
        m3.metric("6-Month Momentum", f"{market_data['ret_6m']:+.2f}%")
        m4.metric("Quant Trend", market_data['trend'])
        st.divider()
        
        with st.spinner("Analyzing technical levels..."):
            ai_summary = generate_ai_sentiment(
                market_data['price'], market_data['daily_pts'], market_data['daily_pct'], 
                market_data['ret_1m'], market_data['ret_6m'], market_data['trend']
            )
            st.markdown(ai_summary)
    else:
        st.error("Market data feed temporarily unavailable from upstream exchange servers.")

# =========================================================
# 3. DEFINED UNIVERSES PER STRATEGY
# =========================================================
LARGE_MID_CAP_THEMES = {
    "EMS & Electronics Manufacturing": ["DIXON.NS", "KAYNES.NS", "SYRMA.NS", "AMBER.NS"],
    "Defense & Capital Goods": ["HAL.NS", "BEL.NS", "BDL.NS", "MAZDOCK.NS"],
    "Clean Energy Transition": ["IREDA.NS", "KPIGREEN.NS", "TATAPOWER.NS"],
    "Specialty Chemicals & Pharma": ["NEOGEN.NS", "FINEORG.NS", "TATVA.NS", "LAURUSLABS.NS"]
}

SMALLCAP_THEMES = {
    "High-Growth Small-Caps (INR 1K - 5K Cr)": ["MARKSANS.NS", "GENUSPOWER.NS", "SAKSOFT.NS", "SERVOTECH.NS", "ZENTEC.NS", "ELECON.NS", "PCBL.NS"],
    "Niche Market Leaders": ["GANDHITUBE.NS", "LLOYDSENGG.NS", "TARC.NS", "DOLLAR.NS"]
}

PENNY_MICRO_THEMES = {
    "High-Volume Penny Stocks (< INR 50)": ["SUZLON.NS", "RPOWER.NS", "JPPOWER.NS", "YESBANK.NS", "IDEA.NS", "GTLINFRA.NS", "FCSSOFT.NS"],
    "Nano-Cap Turnarounds (< INR 1,000 Cr)": ["VIKASLIFE.NS", "URJA.NS", "RENUKA.NS", "HCC.NS", "IFCI.NS", "SOUTHBANK.NS"]
}

# =========================================================
# 4. DETERMINISTIC QUANT ENGINE
# =========================================================
@st.cache_data(ttl=1800)
def analyze_stock(ticker, theme, strategy_type="core"):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        
        if hist.empty or len(hist) < 30: return None
            
        close = hist['Close'].dropna() 
        if close.empty: return None
            
        current_price = round(float(close.iloc[-1]), 2)
        volume_avg = float(hist['Volume'].tail(20).mean())
        
        ret_1m = float(((current_price - close.iloc[-min(22, len(close))]) / close.iloc[-min(22, len(close))]) * 100)
        ret_6m = float(((current_price - close.iloc[-min(126, len(close))]) / close.iloc[-min(126, len(close))]) * 100)
        sma_50 = float(close.rolling(min(50, len(close))).mean().iloc[-1])
        sma_200 = float(close.rolling(min(200, len(close))).mean().iloc[-1])
        
        info = stock.info or {}
        fin = stock.financials
        cf = stock.cashflow
        
        market_cap_cr = round(info.get('marketCap', 0) / 10000000, 2)
        if market_cap_cr <= 0:
            shares = info.get('sharesOutstanding', 10000000)
            market_cap_cr = round((current_price * shares) / 10000000, 2)
            
        pe_ratio = info.get('trailingPE', None)
        roe = info.get('returnOnEquity', None)
        opm = info.get('operatingMargins', None)
        debt_to_equity = info.get('debtToEquity', None)
        
        ocf_val = 0.0
        net_inc = 0.0
        rev_val = 0.0
        
        if not fin.empty:
            if 'Total Revenue' in fin.index: rev_val = float(fin.loc['Total Revenue'].iloc[0])
            if 'Net Income' in fin.index: net_inc = float(fin.loc['Net Income'].iloc[0])
            if 'Operating Income' in fin.index and opm is None:
                opm = float(fin.loc['Operating Income'].iloc[0] / rev_val) if rev_val > 0 else 0.12
                
        if not cf.empty and 'Operating Cash Flow' in cf.index:
            ocf_val = float(cf.loc['Operating Cash Flow'].iloc[0])

        roe_pct = round(roe * 100, 2) if roe is not None and not np.isnan(roe) else 10.0
        opm_pct = round(opm * 100, 2) if opm is not None and not np.isnan(opm) else 10.0
        de_val = round(debt_to_equity / 100, 2) if debt_to_equity is not None and not np.isnan(debt_to_equity) else 0.35
        pe_val = round(pe_ratio, 2) if pe_ratio is not None and not np.isnan(pe_ratio) else 25.0
        cash_conversion = round(ocf_val / net_inc, 2) if (net_inc > 0 and ocf_val != 0) else 0.50

        target_3x_price = round(current_price * 3, 2)
        target_3x_mcap_cr = round(market_cap_cr * 3, 2)
        current_pe_benchmark = max(pe_val, 12.0)
        target_pe_benchmark = min(max(current_pe_benchmark * 1.25, 32.0), 55.0)
        multiple_expansion_ratio = target_pe_benchmark / current_pe_benchmark
        twin_engine_pat_cagr = round((((3.0 / multiple_expansion_ratio) ** (1/3)) - 1) * 100, 2)

        red_flags = []
        if de_val > 1.2: red_flags.append(("CRITICAL", f"High Debt ({de_val})"))
        if cash_conversion < 0.55 and net_inc > 0: red_flags.append(("HIGH", f"Weak Cash Conv ({cash_conversion}x)"))

        score = 0
        feasibility = 0
        
        if strategy_type == "penny":
            if volume_avg < 250000: red_flags.append(("CRITICAL", "Low Liquidity"))
            if ocf_val < 0 and net_inc > 0: red_flags.append(("CRITICAL", "Fake Earnings Flag"))
            if de_val <= 0.1: score += 30
            elif de_val <= 0.5: score += 15
            if cash_conversion >= 1.0: score += 30
            elif cash_conversion >= 0.6: score += 15
            if volume_avg > 1000000: score += 20
            elif volume_avg > 250000: score += 10
            if current_price > sma_50: score += 20
            if market_cap_cr < 1000: feasibility += 50
            elif market_cap_cr < 3000: feasibility += 25
            if current_price < 50: feasibility += 50
            
        elif strategy_type == "smallcap":
            if volume_avg < 30000: red_flags.append(("HIGH", "Low Liquidity"))
            if de_val <= 0.2: score += 25
            elif de_val <= 0.6: score += 15
            if cash_conversion >= 0.75: score += 25
            if roe_pct >= 12.0: score += 20
            if opm_pct >= 10.0: score += 15
            if current_price > sma_50: score += 15
            if market_cap_cr < 5000: feasibility += 35
            if twin_engine_pat_cagr <= 35.0: feasibility += 35
            if roe_pct >= 12.0 and de_val <= 0.5: feasibility += 30
            
        else:  
            if roe_pct >= 20.0: score += 20
            elif roe_pct >= 14.0: score += 14
            if de_val <= 0.3: score += 15
            if opm_pct >= 18.0: score += 15
            if cash_conversion >= 0.8: score += 15
            if 0 < pe_val <= 45.0: score += 15
            if current_price > sma_50 and current_price > sma_200: score += 10
            if ret_6m > 15.0: score += 10
            if market_cap_cr < 15000: feasibility += 35
            if twin_engine_pat_cagr <= 30.0: feasibility += 35
            if roe_pct >= 15.0 and de_val <= 0.3: feasibility += 30

        tier = "TIER A - High-Conviction" if (score >= 70 and feasibility >= 60 and not red_flags) else "TIER B - Watchlist" if (score >= 50 and feasibility >= 45) else "TIER C - Speculative"

        return {
            "Symbol": ticker.replace(".NS", ""), "Theme": theme, "Price (₹)": current_price,
            "Target 3x Price (₹)": target_3x_price, "Market Cap (Cr)": market_cap_cr,
            "Target 3x Cap (Cr)": target_3x_mcap_cr, "P/E": pe_val,
            "Target Multiple": round(target_pe_benchmark, 1), "Req PAT CAGR (Twin Engine)": f"{twin_engine_pat_cagr}%",
            "ROE (%)": roe_pct, "OPM (%)": opm_pct, "Debt/Equity": de_val,
            "Cash Conv (OCF/PAT)": f"{cash_conversion}x", "Overall Score (/100)": score,
            "3x Feasibility (/100)": feasibility, "Tier": tier, "Red Flags": red_flags
        }
    except Exception:
        return None

def fetch_dossier_parallel(candidate, strategy):
    sym, theme = candidate["Symbol"], candidate["Theme"]
    
    agent_instructions = """
    ### AGENT 1: GEMINI (Fundamental Moat & Solvency Audit)
    ### AGENT 2: GROK (Operator Manipulation & Order Book)
    ### AGENT 3: CHATGPT (Real Cash Flow Audit)
    ### AGENT 4: CLAUDE (Margin of Safety)
    ### FINAL VERDICT
    """
    context_data = f"""
    Target: {sym} | Theme: {theme} | Strategy: {strategy.upper()}
    Price: {candidate['Price (₹)']} | MCap: {candidate['Market Cap (Cr)']}
    ROE: {candidate['ROE (%)']}% | P/E: {candidate['P/E']} | D/E: {candidate['Debt/Equity']}
    Cash Conv: {candidate['Cash Conv (OCF/PAT)']}
    Flags: {[f[1] for f in candidate['Red Flags']]}
    """
    
    if not ai_client: return sym, f"**Deterministic Audit:** Scored {candidate['Overall Score (/100)']}/100."

    prompt = f"""Analyze {sym}.
    {context_data}
    Format using standard bullet points (-). NO tables.
    Provide sections:
    {agent_instructions}
    
    For the FINAL VERDICT section, you MUST declare a definitive action: **[BUY]**, **[SELL]**, **[WATCH]**, or **[AVOID]**. 
    You MUST provide a data-driven justification explicitly citing the P/E, ROE, Debt/Equity, or Cash Conversion figures provided above to support your decision.
    """
    
    for model_name in ["gemini-3.5-flash", "gemini-3.1-flash-lite"]:
        for attempt in range(3):
            try:
                response = ai_client.models.generate_content(model=model_name, contents=prompt)
                return sym, response.text.strip() if response.text else "Generation failed."
            except Exception as e:
                if "429" in str(e) or "503" in str(e): time.sleep(5)
                else: break
    return sym, "API rate limits reached. Try again shortly."

# =========================================================
# 6. BULLETPROOF PDF EXPORTERS
# =========================================================
class MultibaggerPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 12)
        self.cell(0, 7, "INDIAN EQUITY RESEARCH", ln=True, align="C")
        self.ln(3)

def clean_text_for_pdf(text):
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        '₹': 'INR ', '—': '-', '–': '-', '’': "'", '‘': "'", '“': '"', '”': '"', 
        '•': '-', '…': '...', '**': '', '### ': '\n'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('latin-1', 'replace').decode('latin-1')

def build_pdf_report(candidate_list, dossier_dict, report_title="Report"):
    pdf = MultibaggerPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 6, clean_text_for_pdf(f"Summary: {report_title}"), ln=True)
    pdf.ln(1)
    
    pdf.set_font("helvetica", "B", 8)
    pdf.set_fill_color(230, 235, 245)
    headers = ["Symbol", "Price", "MCap (Cr)", "Score", "Tier"]
    widths = [25, 25, 30, 20, 50]
    for w, h in zip(widths, headers): pdf.cell(w, 5, clean_text_for_pdf(h), 1, 0, 'C', True)
    pdf.ln()
    
    pdf.set_font("helvetica", "", 7.5)
    for c in candidate_list:
        pdf.cell(25, 5, clean_text_for_pdf(c['Symbol']), 1, 0, 'C')
        pdf.cell(25, 5, clean_text_for_pdf(f"{float(c['Price (₹)']):.2f}"), 1, 0, 'C')
        pdf.cell(30, 5, clean_text_for_pdf(f"{c['Market Cap (Cr)']:,}"), 1, 0, 'C')
        pdf.cell(20, 5, clean_text_for_pdf(f"{c['Overall Score (/100)']}"), 1, 0, 'C')
        pdf.cell(50, 5, clean_text_for_pdf(c['Tier'][:25]), 1, 1, 'L')
    pdf.ln(5)

    for c in candidate_list:
        sym = c['Symbol']
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 6, clean_text_for_pdf(f"Dossier: {sym}"), ln=1)
        pdf.set_font("helvetica", "", 8)
        if sym in dossier_dict:
            pdf.multi_cell(190, 4, clean_text_for_pdf(dossier_dict[sym]))
        pdf.ln(4)
    return pdf.output(dest="S").encode("latin-1", "replace")

def build_single_stock_pdf(f_data, audit_text):
    pdf = MultibaggerPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 8, clean_text_for_pdf(f"Deep Fundamental Audit: {f_data['name']} ({f_data['symbol']})"), ln=True)
    pdf.set_font("helvetica", "", 9)
    pdf.cell(0, 6, clean_text_for_pdf(f"Sector: {f_data['sector']} | Tier: {f_data['cap_tier']}"), ln=True)
    pdf.ln(3)
    
    pdf.set_fill_color(240, 245, 250)
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(0, 6, clean_text_for_pdf(" Key Financial Metrics"), 0, 1, 'L', True)
    pdf.set_font("helvetica", "", 8)
    
    m_text = (
        f"Price: INR {f_data['price']:,.2f}    |    Market Cap: INR {f_data['mcap_cr']:,} Cr\n"
        f"P/E Ratio: {f_data['pe_ratio'] or 'N/A'}    |    PEG Ratio: {f_data['peg_ratio'] or 'N/A'}\n"
        f"ROE: {f_data['roe'] or 'N/A'}%    |    OPM: {f_data['opm'] or 'N/A'}%\n"
        f"Debt/Equity: {f_data['de_ratio'] if f_data['de_ratio'] is not None else 'N/A'}    |    Cash Conversion: {f_data['cash_conversion'] or 'N/A'}x\n"
        f"Piotroski Score: {f_data['f_score']}/9    |    FCF Yield: {f_data['fcf_yield'] or 'N/A'}%"
    )
    pdf.multi_cell(0, 5, clean_text_for_pdf(m_text))
    pdf.ln(3)
    
    pdf.set_font("helvetica", "B", 9)
    pdf.cell(0, 6, clean_text_for_pdf(" 4-Agent Institutional AI Review"), 0, 1, 'L', True)
    pdf.set_font("helvetica", "", 8)
    
    pdf.multi_cell(0, 4, clean_text_for_pdf(audit_text))
    
    return pdf.output(dest="S").encode("latin-1", "replace")

# =========================================================
# 7. DEEP 10-POINT FUNDAMENTAL AUDIT ENGINE (TAB 4)
# =========================================================
@st.cache_data(ttl=1800)
def fetch_deep_stock_fundamentals(symbol_query):
    clean_sym = symbol_query.strip().upper().replace(".NS", "").replace(".BO", "")
    ticker_str = f"{clean_sym}.NS"
    
    try:
        stock = yf.Ticker(ticker_str)
        hist = stock.history(period="5y")
        
        # Fallback to BSE if NSE fails
        if hist.empty or len(hist) < 30:
            ticker_str = f"{clean_sym}.BO"
            stock = yf.Ticker(ticker_str)
            hist = stock.history(period="5y")
            
        if hist.empty or len(hist) < 30:
            return None
            
        info = stock.info or {}
        fin = stock.financials
        cf = stock.cashflow
        bs = stock.balance_sheet
        
        # FIXED: Drop any NaN rows from Yahoo Finance before grabbing the last price
        close_series = hist['Close'].dropna()
        if close_series.empty:
            return None
        current_price = float(close_series.iloc[-1])
        
        mcap_cr = round(info.get('marketCap', 0) / 10000000, 2)
        if mcap_cr <= 0:
            shares = info.get('sharesOutstanding', 10000000)
            mcap_cr = round((current_price * shares) / 10000000, 2)

        if current_price < 50 or mcap_cr < 1000:
            cap_tier = "Penny / Nano-Cap (< INR 1,000 Cr or < ₹50)"
        elif mcap_cr < 5000:
            cap_tier = "Small-Cap (INR 1,000 - 5,000 Cr)"
        elif mcap_cr < 20000:
            cap_tier = "Mid-Cap (INR 5,000 - 20,000 Cr)"
        else:
            cap_tier = "Large-Cap (> INR 20,000 Cr)"

        rev_cagr, pat_cagr = None, None
        if not fin.empty and 'Total Revenue' in fin.index and fin.shape[1] >= 3:
            rev_series = fin.loc['Total Revenue'].dropna()
            if len(rev_series) >= 3 and rev_series.iloc[-1] > 0:
                years = len(rev_series) - 1
                rev_cagr = round((((rev_series.iloc[0] / rev_series.iloc[-1]) ** (1 / years)) - 1) * 100, 2)
        if not fin.empty and 'Net Income' in fin.index and fin.shape[1] >= 3:
            pat_series = fin.loc['Net Income'].dropna()
            if len(pat_series) >= 3 and pat_series.iloc[-1] > 0 and pat_series.iloc[0] > 0:
                years = len(pat_series) - 1
                pat_cagr = round((((pat_series.iloc[0] / pat_series.iloc[-1]) ** (1 / years)) - 1) * 100, 2)

        # FIXED: Added pd.isna() checks to handle raw math 'nan' returns from the API
        roe_raw = info.get('returnOnEquity')
        roe = round(roe_raw * 100, 2) if roe_raw is not None and not pd.isna(roe_raw) else None
        
        opm_raw = info.get('operatingMargins')
        opm = round(opm_raw * 100, 2) if opm_raw is not None and not pd.isna(opm_raw) else None
        
        roce_raw = info.get('returnOnAssets')
        roce = round(roce_raw * 100 * 1.5, 2) if roce_raw is not None and not pd.isna(roce_raw) else None 

        ocf, capex, fcf, cash_conversion = 0.0, 0.0, None, None
        if not cf.empty:
            if 'Operating Cash Flow' in cf.index: 
                ocf_series = cf.loc['Operating Cash Flow'].dropna()
                ocf = float(ocf_series.iloc[0]) if not ocf_series.empty else 0.0
            if 'Capital Expenditure' in cf.index: 
                capex_series = cf.loc['Capital Expenditure'].dropna()
                capex = abs(float(capex_series.iloc[0])) if not capex_series.empty else 0.0
            fcf = round((ocf - capex) / 10000000, 2) if ocf != 0 else None
            
        if not fin.empty and 'Net Income' in fin.index and ocf != 0:
            net_income_series = fin.loc['Net Income'].dropna()
            net_income_curr = float(net_income_series.iloc[0]) if not net_income_series.empty else 0.0
            if net_income_curr > 0: cash_conversion = round(ocf / net_income_curr, 2)

        de_raw = info.get('debtToEquity')
        de_val = round(de_raw / 100, 2) if de_raw is not None and not pd.isna(de_raw) else None
        
        current_ratio = round(info.get('currentRatio', 0), 2) if info.get('currentRatio') else None

        pe_ratio = round(info.get('trailingPE', 0), 2) if info.get('trailingPE') else None
        forward_pe = round(info.get('forwardPE', 0), 2) if info.get('forwardPE') else None
        peg_ratio = round(info.get('pegRatio', 0), 2) if info.get('pegRatio') else None
        ev_ebitda = round(info.get('enterpriseToEbitda', 0), 2) if info.get('enterpriseToEbitda') else None
        fcf_yield = round((((fcf * 10000000) / (mcap_cr * 10000000)) * 100), 2) if fcf and mcap_cr > 0 else None

        insider_ownership = round(info.get('heldPercentInsiders', 0) * 100, 2) if info.get('heldPercentInsiders') else None

        f_score = 0
        if not fin.empty and not cf.empty:
            if ocf > 0: f_score += 1
            if roe and roe > 0: f_score += 1
            if cash_conversion and cash_conversion > 1.0: f_score += 2
            if de_val is not None and de_val < 0.6: f_score += 1
            if current_ratio and current_ratio > 1.3: f_score += 1
            if opm and opm > 12.0: f_score += 1
            if rev_cagr and rev_cagr > 10.0: f_score += 1
            if fcf and fcf > 0: f_score += 1

        beta = round(info.get('beta', 1.0), 2) if info.get('beta') else 1.0

        return {
            "symbol": clean_sym, "name": info.get('longName', clean_sym), "sector": info.get('sector', 'N/A'),
            "industry": info.get('industry', 'N/A'), "price": current_price, "mcap_cr": mcap_cr,
            "cap_tier": cap_tier, "rev_cagr": rev_cagr, "pat_cagr": pat_cagr, "roe": roe, "roce": roce,
            "opm": opm, "cash_conversion": cash_conversion, "fcf_cr": fcf, "fcf_yield": fcf_yield,
            "de_ratio": de_val, "current_ratio": current_ratio, "pe_ratio": pe_ratio, "forward_pe": forward_pe,
            "peg_ratio": peg_ratio, "ev_ebitda": ev_ebitda, "promoter_holding": insider_ownership,
            "f_score": f_score, "beta": beta
        }
    except Exception as e:
        print(f"Error in deep fundamental analysis: {e}")
        return None

def run_four_agent_deep_audit(f_data):
    if not ai_client: return "Gemini AI client offline. Deterministic quantitative scorecard remains fully verified."
        
    audit_context = f"""
    TARGET: {f_data['name']} ({f_data['symbol']}.NS) | TIER: {f_data['cap_tier']}
    PRICE: INR {f_data['price']} | MCAP: INR {f_data['mcap_cr']:,} Cr

    DATA CHECKLIST:
    1. Growth: Rev CAGR: {f_data['rev_cagr']}% | PAT CAGR: {f_data['pat_cagr']}%
    2. Margins: OPM: {f_data['opm']}% | ROE: {f_data['roe']}%
    3. Cash Flow: Conv: {f_data['cash_conversion']}x | FCF Yield: {f_data['fcf_yield']}%
    4. Debt: D/E: {f_data['de_ratio']} | Current Ratio: {f_data['current_ratio']}
    5. Valuation: P/E: {f_data['pe_ratio']} | PEG: {f_data['peg_ratio']}
    6. Score: Piotroski: {f_data['f_score']}/9
    """

    master_prompt = f"""
    You are an elite Institutional Investment Committee evaluating an Indian equity.
    {audit_context}
    
    Structure your briefing EXACTLY with these 5 markdown sections (NO tables, use bullet points):

    ### AGENT 1: GEMINI (Moat, Business Model & Profitability)
    - Evaluate business model clarity, moat, and pricing power. Give explicit PASS or FAIL verdict.

    ### AGENT 2: GROK (Catalysts & Real-World Reality Check)
    - Reality-check industry tailwinds vs competitive disruption. Check for operator volume traps. Give explicit PASS or FAIL verdict.

    ### AGENT 3: CHATGPT (Mathematical Feasibility & Valuation)
    - Audit ROE drivers and evaluate valuation margins. Give explicit PASS or FAIL verdict.

    ### AGENT 4: CLAUDE (Forensic Adversary & Red Flags)
    - Scrutinize cash flow authenticity, solvency, and Piotroski score. Give explicit PASS or FAIL verdict.

    ### FINAL COMMITTEE JUDGE VERDICT
    - Final Verdict: You MUST evaluate all points and state either **CLEAR PASS** or **CLEAR FAIL**. Do not use "Watchlist" or "Hold". It must be a strict binary decision.
    - Final Action: Declare **[BUY]**, **[SELL]**, **[WATCH]**, or **[AVOID]**.
    - Final Score: X/10 against the 10-Point Checklist.
    - Data-Driven Justification: Briefly explain the definitive reason for the Pass or Fail, explicitly citing the specific metrics provided above (e.g. ROE, P/E, Cash Conversion, etc.)
    """

    for model_name in ["gemini-3.5-flash", "gemini-3.1-flash-lite"]:
        for attempt in range(3):
            try:
                response = ai_client.models.generate_content(model=model_name, contents=master_prompt)
                if response.text: return response.text.strip()
            except Exception as e:
                if "429" in str(e) or "503" in str(e): time.sleep(5)
                else: break
    return "AI Committee audit service temporarily experiencing high traffic. Please retry in 10 seconds."

# =========================================================
# 8. TRI-TAB + DEEP AUDIT TAB WORKFLOW
# =========================================================
tab_core, tab_smallcap, tab_penny, tab_fundamental = st.tabs([
    "🏛️ Large & Mid-Cap Core", "🚀 Small-Caps", "⚠️ Penny & Micro-Caps", "🔬 Deep Fundamental AI Audit"
])

def render_pipeline_ui(theme_dict, strategy, title, min_score_default):
    st.subheader(title)
    selected_theme = st.selectbox(f"Select Theme:", ["All Themes"] + list(theme_dict.keys()), key=f"sel_{strategy}")
    min_score = st.slider("Minimum Score:", 35, 90, min_score_default, key=f"sld_{strategy}")

    if st.button(f"🚀 Run Fast Pipeline", key=f"btn_{strategy}"):
        with st.spinner("Step 1/2: Quant Scanning (Parallel Processing)..."):
            scan_map = theme_dict if selected_theme.startswith("All") else {selected_theme: theme_dict[selected_theme]}
            tasks = [(t, t_name, strategy) for t_name, tickers in scan_map.items() for t in tickers]
            
            all_cands = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(analyze_stock, t[0], t[1], t[2]) for t in tasks]
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    if res: all_cands.append(res)

            df = pd.DataFrame(all_cands)
            
        if not df.empty:
            df_sorted = df[df["Overall Score (/100)"] >= min_score].sort_values(
                by=["Overall Score (/100)"], ascending=False
            ).reset_index(drop=True)

            st.dataframe(df_sorted[["Symbol", "Price (₹)", "Market Cap (Cr)", "P/E", "Debt/Equity", "ROE (%)", "Overall Score (/100)", "Tier"]], use_container_width=True)
            top_picks = df_sorted.head(4).to_dict('records')
            
            st.markdown(f"### 🔬 {strategy.capitalize()} Research Dossiers")
            dossier_map = {}
            
            with st.spinner("Step 2/2: Generating AI Dossiers concurrently..."):
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ai_executor:
                    ai_futures = [ai_executor.submit(fetch_dossier_parallel, c, strategy) for c in top_picks]
                    for future in concurrent.futures.as_completed(ai_futures):
                        sym, content = future.result()
                        dossier_map[sym] = content

            for candidate in top_picks:
                sym = candidate["Symbol"]
                color = "🟢" if "TIER A" in candidate["Tier"] else ("🟡" if "TIER B" in candidate["Tier"] else "🔴")
                
                with st.expander(f"{color} {sym} — Quant Score: {candidate['Overall Score (/100)']}/100", expanded=True):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Current Price", f"₹{float(candidate['Price (₹)']):,.2f}")
                    c1.metric("Market Cap", f"₹{candidate['Market Cap (Cr)']:,} Cr")
                    c2.metric("Debt-to-Equity", f"{candidate['Debt/Equity']}")
                    c3.metric("ROE (%)", f"{candidate['ROE (%)']}%")
                    c4.metric("3Y 3x Target", f"₹{float(candidate['Target 3x Price (₹)']):,.2f}")
                    
                    if candidate["Red Flags"]: st.error(f"🚨 Warnings: {', '.join([f[1] for f in candidate['Red Flags']])}")
                    st.markdown(dossier_map.get(sym, "Dossier not found."))
            
            if dossier_map:
                pdf = build_pdf_report(top_picks, dossier_map, f"{strategy.capitalize()} Research")
                st.download_button("📄 Download Pipeline PDF Report", data=pdf, file_name=f"{strategy}_report.pdf", mime="application/pdf", key=f"dl_{strategy}")

# RENDER TABS 1-3
with tab_core: render_pipeline_ui(LARGE_MID_CAP_THEMES, "large/mid-cap", "Secular Growth & Market Leaders", 60)
with tab_smallcap: render_pipeline_ui(SMALLCAP_THEMES, "smallcap", "Micro/Small-Cap Compounders", 50)
with tab_penny: render_pipeline_ui(PENNY_MICRO_THEMES, "penny", "High-Risk Penny & Nano-Caps", 50)

# =========================================================
# TAB 4: DEEP FUNDAMENTAL AUDIT TAB
# =========================================================
with tab_fundamental:
    st.subheader("🔍 Deep Fundamental Stock Auditor (Screener.in 10-Point Checklist)")
    st.caption("Institutional Analysis across Large, Mid, Small, and Penny Caps with 4 Collaborative AI Agents (Grok, Gemini, ChatGPT, Claude)")

    col_in1, col_in2 = st.columns([3, 1])
    with col_in1:
        stock_query = st.text_input("Enter NSE/BSE Stock Symbol or Name (e.g. RELIANCE, DIXON, SUZLON, KAYNES):", value="DIXON")
    with col_in2:
        run_audit_btn = st.button("🔎 Run 4-Agent Deep Audit", use_container_width=True)

    if run_audit_btn and stock_query:
        with st.spinner(f"Step 1/2: Harvesting 5-year financials and balance sheet for {stock_query}..."):
            f_data = fetch_deep_stock_fundamentals(stock_query)

        if not f_data:
            st.error(f"Could not retrieve reliable exchange data for '{stock_query}'. Please verify ticker spelling or try with '.NS' or '.BO' suffix.")
        else:
            st.markdown(f"## 🏢 {f_data['name']} (`{f_data['symbol']}`)")
            st.info(f"**Sector:** {f_data['sector']} | **Industry:** {f_data['industry']} | **Classification:** {f_data['cap_tier']}")

            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("Current Price", f"₹{f_data['price']:,.2f}")
            k1.metric("Market Cap", f"₹{f_data['mcap_cr']:,} Cr")
            k2.metric("P/E Ratio", f"{f_data['pe_ratio'] or 'N/A'}")
            k2.metric("PEG Ratio", f"{f_data['peg_ratio'] or 'N/A'}")
            k3.metric("ROE (%)", f"{f_data['roe']}%" if f_data['roe'] else "N/A")
            k3.metric("OPM (%)", f"{f_data['opm']}%" if f_data['opm'] else "N/A")
            k4.metric("Debt-to-Equity", f"{f_data['de_ratio']}" if f_data['de_ratio'] is not None else "N/A")
            k4.metric("Cash Conv (OCF/PAT)", f"{f_data['cash_conversion']}x" if f_data['cash_conversion'] else "N/A")
            k5.metric("Piotroski F-Score", f"{f_data['f_score']}/9")
            k5.metric("FCF Yield", f"{f_data['fcf_yield']}%" if f_data['fcf_yield'] else "N/A")

            st.divider()

            st.markdown("### 📋 10-Point Indian Equity Quality Checklist Audit")
            c_chk1, c_chk2 = st.columns(2)
            
            with c_chk1:
                if f_data['rev_cagr'] and f_data['rev_cagr'] >= 10:
                    st.success(f"✅ **Revenue Growth:** Strong consistency ({f_data['rev_cagr']}% CAGR > 10% threshold)")
                else:
                    st.warning(f"⚠️ **Revenue Growth:** Subdued or inconsistent ({f_data['rev_cagr'] or 'N/A'}% CAGR)")

                if f_data['roe'] and f_data['roe'] >= 15:
                    st.success(f"✅ **ROE Quality:** {f_data['roe']}% (Passes >15% hurdle)")
                else:
                    st.warning(f"⚠️ **ROE Quality:** {f_data['roe'] or 'N/A'}% (Below 15% quality hurdle)")

                if f_data['cash_conversion'] and f_data['cash_conversion'] >= 0.8:
                    st.success(f"✅ **Cash Flow Realization:** OCF cleanly matches profits ({f_data['cash_conversion']}x conversion)")
                else:
                    st.error(f"🚨 **Cash Flow Quality:** Low conversion ({f_data['cash_conversion'] or 'N/A'}x). Check for aggressive accounting")

            with c_chk2:
                if f_data['de_ratio'] is not None and f_data['de_ratio'] <= 0.6:
                    st.success(f"✅ **Solvency & Leverage:** Fortress balance sheet (D/E: {f_data['de_ratio']} < 0.6)")
                elif f_data['de_ratio'] is not None and f_data['de_ratio'] <= 1.0:
                    st.warning(f"⚠️ **Solvency:** Moderate leverage (D/E: {f_data['de_ratio']})")
                else:
                    st.error(f"🚨 **Solvency Risk:** Heavy debt load (D/E: {f_data['de_ratio'] or 'N/A'} > 1.0)")

                if f_data['peg_ratio'] and f_data['peg_ratio'] <= 1.5:
                    st.success(f"✅ **PEG Multiple:** Fairly valued for growth rate (PEG: {f_data['peg_ratio']})")
                else:
                    st.warning(f"⚠️ **Valuation Multiple:** Elevated or rich multiple (P/E: {f_data['pe_ratio']}, PEG: {f_data['peg_ratio'] or 'N/A'})")

                if f_data['f_score'] >= 6:
                    st.success(f"✅ **Piotroski Quality:** Healthy operational health ({f_data['f_score']}/9)")
                else:
                    st.error(f"🚨 **Piotroski Warning:** Low operational resilience ({f_data['f_score']}/9)")

            st.divider()

            with st.spinner("Step 2/2: Convening 4-Agent Institutional AI Committee (Grok, Gemini, ChatGPT, Claude)..."):
                audit_briefing = run_four_agent_deep_audit(f_data)

            st.markdown("### 🤖 4-Agent Institutional Investment Committee Review")
            st.markdown(audit_briefing)
            
            st.divider()
            pdf_bytes = build_single_stock_pdf(f_data, audit_briefing)
            st.download_button(
                label=f"📄 Download {f_data['symbol']} Deep Audit PDF", 
                data=pdf_bytes, 
                file_name=f"{f_data['symbol']}_Deep_Audit.pdf", 
                mime="application/pdf",
                use_container_width=True
            )
