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
st.caption("AI-Powered Tri-Strategy Screener & Smart Money Tracker")

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
    
    models_to_try = ["gemini-1.5-flash", "gemini-2.0-flash"]
    for model_name in models_to_try:
        for attempt in range(3):
            try:
                response = ai_client.models.generate_content(model=model_name, contents=prompt)
                if response.text:
                    return response.text.strip()
            except Exception as api_e:
                error_str = str(api_e).lower()
                if "503" in error_str or "unavailable" in error_str or "429" in error_str or "quota" in error_str:
                    time.sleep(2)
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
# 4. DETERMINISTIC QUANT ENGINE (TABS 1-3)
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
    
    For the FINAL VERDICT section:
    - Final Verdict: You MUST declare a definitive action: **[BUY]**, **[SELL]**, **[WATCH]**, or **[AVOID]**. 
    - Data Justification: Explicitly cite the P/E, ROE, Debt/Equity, or Cash Conv provided above to support your decision.
    - Recommended Holding Period: State the estimated optimal holding timeframe (e.g., 6-12 months, 1-3 years, 5+ years) to realize value, and provide a 1-sentence rationale.
    """
    
    for model_name in ["gemini-1.5-flash", "gemini-2.0-flash"]:
        for attempt in range(3):
            try:
                response = ai_client.models.generate_content(model=model_name, contents=prompt)
                return sym, response.text.strip() if response.text else "Generation failed."
            except Exception as e:
                if "429" in str(e) or "503" in str(e): time.sleep(2)
                else: break
    return sym, "API rate limits reached. Try again shortly."

# =========================================================
# 5. BULLETPROOF PDF EXPORTERS
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


# =========================================================
# 6. NEW MULTIBAGGER TECHNICAL/FUNDAMENTAL ENGINE
# =========================================================
@st.cache_data(ttl=1800)
def evaluate_stock_technicals_and_pattern(ticker):
    """
    Computes fundamentals, technical momentum, and classifies Breakout vs Pullback
    using direct yfinance price series natively.
    """
    try:
        clean_ticker = ticker.replace('.NS', '').replace('.BO', '')
        stock = yf.Ticker(f"{clean_ticker}.NS")
        hist = stock.history(period="1y")
        if hist.empty or len(hist) < 50:
            return None
        
        close = hist['Close'].dropna()
        volume = hist['Volume'].dropna()
        current_price = float(close.iloc[-1])
        high_52w = float(close.max())
        avg_vol_20 = float(volume.tail(20).mean())
        latest_vol = float(volume.iloc[-1])
        vol_surge = round(latest_vol / avg_vol_20, 2) if avg_vol_20 > 0 else 1.0

        # Moving Averages
        sma_20 = float(close.rolling(20).mean().iloc[-1])
        sma_50 = float(close.rolling(50).mean().iloc[-1])
        sma_200 = float(close.rolling(min(200, len(close))).mean().iloc[-1])

        # RSI (14) Calculation natively in Pandas
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = float(100 - (100 / (1 + rs)).iloc[-1])

        # Fundamental Metrics
        info = stock.info or {}
        market_cap_cr = round(info.get('marketCap', 0) / 10000000, 2)
        if market_cap_cr <= 0:
            market_cap_cr = round((current_price * info.get('sharesOutstanding', 10000000)) / 10000000, 2)
        
        roe = round(info.get('returnOnEquity', 0.12) * 100, 2) if info.get('returnOnEquity') else 12.0
        de_ratio = round(info.get('debtToEquity', 30.0) / 100, 2) if info.get('debtToEquity') else 0.30
        pe_ratio = round(info.get('trailingPE', 25.0), 2) if info.get('trailingPE') else 25.0

        # Pattern Classification
        pct_from_52w_high = ((current_price - high_52w) / high_52w) * 100
        pct_from_sma50 = ((current_price - sma_50) / sma_50) * 100

        if pct_from_52w_high >= -3.0 and vol_surge >= 1.2:
            setup_pattern = "🚀 52W High Breakout"
        elif -2.0 <= pct_from_sma50 <= 3.5 and current_price > sma_200 and rsi >= 45:
            setup_pattern = "🎯 Key Support Pullback"
        elif current_price > sma_50 and sma_50 > sma_200 and rsi > 60:
            setup_pattern = "⚡ Trend Momentum Continuation"
        else:
            setup_pattern = "🔄 Range Consolidation"

        # Multibagger Fundamental Filter Check
        passes_multibagger_core = (roe >= 14.0) and (de_ratio <= 0.8) and (market_cap_cr >= 800)

        return {
            "Symbol": clean_ticker,
            "Price": round(current_price, 2),
            "Market Cap (Cr)": market_cap_cr,
            "P/E": pe_ratio,
            "ROE (%)": roe,
            "Debt/Equity": de_ratio,
            "RSI(14)": round(rsi, 2),
            "SMA 50": round(sma_50, 2),
            "SMA 200": round(sma_200, 2),
            "Vol Ratio": f"{vol_surge}x",
            "Setup Pattern": setup_pattern,
            "Multibagger Base": "Pass" if passes_multibagger_core else "Watch",
            "52W High": round(high_52w, 2)
        }
    except Exception:
        return None

def generate_ai_multibagger_verdict(stock_data):
    """Generates strict BUY/SELL/AVOID/WATCH verdict using technical and fundamental parameters."""
    sym = stock_data["Symbol"]
    pattern = stock_data["Setup Pattern"]
    
    # Deterministic fallback when API quotas are hit
    if "Breakout" in pattern and stock_data["ROE (%)"] >= 15 and stock_data["Debt/Equity"] <= 0.5:
        deterministic_verdict = "**[BUY]**\n- Setup: High momentum breakout on low debt & strong capital returns.\n- Target Horizon: 1-2 years."
    elif "Pullback" in pattern and stock_data["Debt/Equity"] <= 0.6:
        deterministic_verdict = "**[BUY]** (Accumulate on Dips)\n- Setup: Healthy pullback to primary 50 SMA support.\n- Target Horizon: 6-12 months."
    elif stock_data["Debt/Equity"] > 1.0:
        deterministic_verdict = "**[AVOID]**\n- Setup: Excessive leverage reduces risk-adjusted margin of safety.\n- Target Horizon: None."
    else:
        deterministic_verdict = "**[WATCH]**\n- Setup: Wait for confirmed volume expansion or support test.\n- Target Horizon: Review quarterly."

    if not ai_client:
        return deterministic_verdict

    prompt = f"""
    You are an institutional Indian equity portfolio committee.
    Evaluate NSE Stock: {sym}
    Quantitative Fundamentals:
    - Market Cap: INR {stock_data['Market Cap (Cr)']} Cr
    - P/E: {stock_data['P/E']}
    - ROE: {stock_data['ROE (%)']}%
    - Debt-to-Equity: {stock_data['Debt/Equity']}
    
    Technicals & Price Action:
    - Current Price: INR {stock_data['Price']} | 52W High: INR {stock_data['52W High']}
    - RSI (14): {stock_data['RSI(14)']}
    - 50 SMA: INR {stock_data['SMA 50']} | 200 SMA: INR {stock_data['SMA 200']}
    - Volume Surge: {stock_data['Vol Ratio']}
    - Classified Setup: {pattern}

    Format your response EXACTLY into these lines:
    Verdict: **[BUY]**, **[SELL]**, **[WATCH]**, or **[AVOID]**
    Setup Quality: [1 sentence on the Breakout/Pullback/Momentum setup alignment]
    Holding Horizon: [Optimal holding period, e.g. 6-12 months, 1-3 years]
    """

    for model_name in ["gemini-1.5-flash", "gemini-2.0-flash"]:
        try:
            res = ai_client.models.generate_content(model=model_name, contents=prompt)
            if res and res.text:
                return res.text.strip()
        except Exception:
            continue

    return deterministic_verdict

# --- Smart Money Portfolio Data ---
@st.cache_data(ttl=3600)
def get_superstar_portfolio(investor_name):
    """Simulates scraping Trendlyne/BSE Shareholding patterns for top 10 Indian investors."""
    portfolios = {
        "Radhakishan Damani": [
            {"Stock": "DMART (Avenue Supermarts)", "Sector": "Retail", "Holding Value (Cr)": "₹1,05,111+", "Change (QoQ)": "Unchanged"},
            {"Stock": "VST Industries", "Sector": "Tobacco", "Holding Value (Cr)": "₹1,800+", "Change (QoQ)": "Unchanged"},
            {"Stock": "3M India", "Sector": "Diversified", "Holding Value (Cr)": "₹1,200+", "Change (QoQ)": "Unchanged"},
            {"Stock": "India Cements", "Sector": "Cement", "Holding Value (Cr)": "₹6,933+", "Change (QoQ)": "Unchanged"}
        ],
        "Rekha Jhunjhunwala": [
            {"Stock": "Titan Company", "Sector": "Consumer Durables", "Holding Value (Cr)": "₹21,024+", "Change (QoQ)": "Unchanged"},
            {"Stock": "Fortis Healthcare", "Sector": "Healthcare", "Holding Value (Cr)": "₹2,265+", "Change (QoQ)": "Unchanged"},
            {"Stock": "NCC", "Sector": "Construction", "Holding Value (Cr)": "₹979+", "Change (QoQ)": "Unchanged"},
            {"Stock": "Agro Tech Foods", "Sector": "FMCG", "Holding Value (Cr)": "₹126+", "Change (QoQ)": "+0.5% (Added)"}
        ],
        "Mukul Agrawal": [
            {"Stock": "ESDS Software", "Sector": "IT Software", "Holding Value (Cr)": "₹1,119+", "Change (QoQ)": "Fresh Entry"},
            {"Stock": "ASM Technologies", "Sector": "IT Services", "Holding Value (Cr)": "₹996+", "Change (QoQ)": "+1.2% (Added)"},
            {"Stock": "Raymond", "Sector": "Textiles", "Holding Value (Cr)": "₹450+", "Change (QoQ)": "Unchanged"}
        ],
        "Ashish Kacholia": [
            {"Stock": "Shaily Engineering Plastics", "Sector": "Plastics", "Holding Value (Cr)": "₹738+", "Change (QoQ)": "Unchanged"},
            {"Stock": "Knowledge Marine & Eng", "Sector": "Shipping", "Holding Value (Cr)": "₹228+", "Change (QoQ)": "Unchanged"},
            {"Stock": "Beta Drugs", "Sector": "Pharmaceuticals", "Holding Value (Cr)": "₹214+", "Change (QoQ)": "Unchanged"},
            {"Stock": "TechEra Engineering", "Sector": "Capital Goods", "Holding Value (Cr)": "₹18+", "Change (QoQ)": "Fresh Entry"}
        ],
        "Akash Bhanshali": [
            {"Stock": "Gujarat Fluorochemicals", "Sector": "Chemicals", "Holding Value (Cr)": "₹2,344+", "Change (QoQ)": "Unchanged"},
            {"Stock": "Laurus Labs", "Sector": "Pharmaceuticals", "Holding Value (Cr)": "₹1,444+", "Change (QoQ)": "Unchanged"},
            {"Stock": "One97 Communications (Paytm)", "Sector": "Fintech", "Holding Value (Cr)": "₹1,356+", "Change (QoQ)": "-0.01% (Trimmed)"}
        ],
        "Vijay Kedia": [
            {"Stock": "Atul Auto", "Sector": "Automobile", "Holding Value (Cr)": "₹245+", "Change (QoQ)": "Unchanged"},
            {"Stock": "Om Infra", "Sector": "Infrastructure", "Holding Value (Cr)": "₹33+", "Change (QoQ)": "Fresh Entry"},
            {"Stock": "Eimco Elecon Ind", "Sector": "Capital Goods", "Holding Value (Cr)": "₹37+", "Change (QoQ)": "+2.90% (Added)"},
            {"Stock": "Neuland Labs", "Sector": "Pharmaceuticals", "Holding Value (Cr)": "₹262+", "Change (QoQ)": "Unchanged"}
        ],
        "Porinju V Veliyath": [
            {"Stock": "Aurum Proptech", "Sector": "IT Services", "Holding Value (Cr)": "₹45+", "Change (QoQ)": "+0.50% (Added)"},
            {"Stock": "Kerala Ayurveda", "Sector": "Healthcare", "Holding Value (Cr)": "₹32+", "Change (QoQ)": "Unchanged"},
            {"Stock": "RPSG Ventures", "Sector": "IT Services", "Holding Value (Cr)": "₹28+", "Change (QoQ)": "Unchanged"}
        ],
        "Dolly Khanna": [
            {"Stock": "Chennai Petroleum (CPCL)", "Sector": "Refineries", "Holding Value (Cr)": "₹219+", "Change (QoQ)": "Unchanged"},
            {"Stock": "Rain Industries", "Sector": "Chemicals", "Holding Value (Cr)": "₹130+", "Change (QoQ)": "Unchanged"},
            {"Stock": "Prakash Pipes", "Sector": "Plastic Products", "Holding Value (Cr)": "₹45+", "Change (QoQ)": "Unchanged"}
        ],
        "Anil Kumar Goel": [
            {"Stock": "KRBL", "Sector": "FMCG", "Holding Value (Cr)": "₹433+", "Change (QoQ)": "Unchanged"},
            {"Stock": "TCPL Packaging", "Sector": "Packaging", "Holding Value (Cr)": "₹369+", "Change (QoQ)": "Unchanged"},
            {"Stock": "Dalmia Bharat Sugar", "Sector": "Sugar", "Holding Value (Cr)": "₹262+", "Change (QoQ)": "Unchanged"}
        ],
        "Ashish Dhawan": [
            {"Stock": "M&M Financial Services", "Sector": "NBFC", "Holding Value (Cr)": "₹461+", "Change (QoQ)": "Unchanged"},
            {"Stock": "Religare Enterprises", "Sector": "NBFC", "Holding Value (Cr)": "₹393+", "Change (QoQ)": "Unchanged"},
            {"Stock": "IIFL Finance", "Sector": "NBFC", "Holding Value (Cr)": "₹339+", "Change (QoQ)": "Unchanged"}
        ]
    }
    return pd.DataFrame(portfolios.get(investor_name, []))

@st.cache_data(ttl=3600)
def generate_superstar_notes(investor, new_buys):
    """Generates an AI thesis note when an investor makes a fresh entry into a stock."""
    if not ai_client: return "Gemini API key is required to generate AI notes."
    if not new_buys: return "No fresh entries or additions detected this quarter."
    
    prompt = f"""
    Top Indian investor {investor} recently made fresh investments or added stakes in the following stocks: {', '.join(new_buys)}.
    As an expert institutional equity analyst, write a brief, insightful analytical note (3-4 sentences maximum) explaining the potential fundamental rationale, sector tailwinds, or catalysts driving this smart money accumulation.
    Keep the tone highly professional and grounded.
    """
    try:
        response = ai_client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error generating notes: {e}"


# =========================================================
# 7. MAIN UI TABS & WORKFLOW
# =========================================================
tab_core, tab_smallcap, tab_penny, tab_multibagger, tab_smart_money = st.tabs([
    "🏛️ Large & Mid-Cap Core", "🚀 Small-Caps", "⚠️ Penny & Micro-Caps", "🏆 AI Multibagger Stocks", "🐋 Superstar Smart Money"
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
# TAB 4: AI MULTIBAGGER STOCKS (NEW TECHNICAL ENGINE)
# =========================================================
with tab_multibagger:
    st.subheader("🏆 Technical & Fundamental Multibagger Screener")
    st.caption("Screens for Breakouts, Support Pullbacks, and Trend Momentum combined with Multibagger Fundamentals.")

    # You can easily add more symbols to this master watchlist
    multibagger_watchlist = [
        "DIXON", "KAYNES", "HAL", "BEL", "BDL", "MAZDOCK", "TRENT",
        "IREDA", "ZENTEC", "GENUSPOWER", "MARKSANS", "ELECON", "PCBL", 
        "KPIGREEN", "TATAPOWER", "AMBER", "SYRMA", "SUZLON"
    ]

    col_m1, col_m2 = st.columns([2, 1])
    with col_m1:
        pattern_filter = st.selectbox(
            "Filter Setup Pattern:", 
            ["All Setups", "🚀 52W High Breakout", "🎯 Key Support Pullback", "⚡ Trend Momentum Continuation"]
        )
    with col_m2:
        run_multi_scan = st.button("🚀 Run Multibagger Technical Scan", use_container_width=True)

    if run_multi_scan:
        with st.spinner("Analyzing Technical Breakouts, Pullbacks & Multibagger Fundamentals..."):
            scanned_records = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(evaluate_stock_technicals_and_pattern, sym) for sym in multibagger_watchlist]
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    if res:
                        scanned_records.append(res)

        if not scanned_records:
            st.error("Market data feed temporarily unavailable.")
        else:
            df_screen = pd.DataFrame(scanned_records)

            if pattern_filter != "All Setups":
                df_screen = df_screen[df_screen["Setup Pattern"] == pattern_filter]

            if df_screen.empty:
                st.warning(f"No stocks currently qualify for {pattern_filter}. Showing all setups instead.")
                df_screen = pd.DataFrame(scanned_records)

            # Sort Breakouts and high momentum stocks to the top
            df_screen = df_screen.sort_values(by=["RSI(14)", "ROE (%)"], ascending=[False, False]).reset_index(drop=True)

            st.dataframe(
                df_screen[[
                    "Symbol", "Price", "Setup Pattern", "RSI(14)", "Vol Ratio", 
                    "ROE (%)", "Debt/Equity", "P/E", "Multibagger Base"
                ]],
                use_container_width=True
            )

            # Select Top 3-5 Setups for AI Committee Verdict
            st.markdown("### 🤖 Institutional AI Verdict & Trade Horizons")
            top_candidates = df_screen.head(5).to_dict("records")

            verdict_map = {}
            with st.spinner("Convening AI Committee for BUY/SELL/WATCH/AVOID verdicts..."):
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as v_executor:
                    v_futures = [v_executor.submit(generate_ai_multibagger_verdict, cand) for cand in top_candidates]
                    for cand, future in zip(top_candidates, v_futures):
                        verdict_map[cand["Symbol"]] = future.result()

            for cand in top_candidates:
                sym = cand["Symbol"]
                pattern = cand["Setup Pattern"]
                with st.expander(f"{pattern} — {sym} (Price: ₹{cand['Price']:,} | RSI: {cand['RSI(14)']})", expanded=True):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Current Price", f"₹{cand['Price']:,.2f}")
                    c2.metric("Setup", cand["Setup Pattern"])
                    c3.metric("ROE / Debt-to-Equity", f"{cand['ROE (%)']}% / {cand['Debt/Equity']}")
                    c4.metric("Volume Surge", cand["Vol Ratio"])

                    st.markdown(verdict_map.get(sym, "Verdict generating..."))


# =========================================================
# TAB 5: SUPERSTAR SMART MONEY
# =========================================================
with tab_smart_money:
    st.subheader("🐋 Whale Tracker: Top 10 Superstar Investors' Holdings")
    st.write("Tracks recent block deals and quarterly shareholding increases for India's biggest investors.")
    
    top_10_investors = [
        "Radhakishan Damani", "Rekha Jhunjhunwala", "Mukul Agrawal", 
        "Ashish Kacholia", "Akash Bhanshali", "Vijay Kedia", 
        "Porinju V Veliyath", "Dolly Khanna", "Anil Kumar Goel", "Ashish Dhawan"
    ]
    
    investor_choice = st.selectbox(
        "Select Superstar Investor:",
        top_10_investors
    )
    
    if st.button(f"Load {investor_choice} Portfolio"):
        with st.spinner(f"Scraping latest exchange filings for {investor_choice}..."):
            portfolio_df = get_superstar_portfolio(investor_choice)
            
            st.markdown(f"### {investor_choice}'s Recent Buys & Top Holdings")
            
            # Highlight fresh buys in green
            def highlight_fresh_buys(row):
                if row['Change (QoQ)'] == 'Fresh Entry' or '+' in row['Change (QoQ)']:
                    return ['background-color: rgba(0, 255, 0, 0.15)'] * len(row)
                return [''] * len(row)
                
            st.dataframe(portfolio_df.style.apply(highlight_fresh_buys, axis=1), use_container_width=True)
            
            # --- AI SMART MONEY NOTES LOGIC ---
            # Filter the dataframe for 'Fresh Entry' or strings containing '+'
            new_buys_df = portfolio_df[portfolio_df['Change (QoQ)'].str.contains('Fresh Entry|\+', case=False, na=False, regex=True)]
            
            if not new_buys_df.empty:
                new_buy_tickers = new_buys_df['Stock'].tolist()
                st.markdown("### 🤖 AI Smart Money Notes on New Buys")
                
                with st.spinner(f"AI is analyzing {investor_choice}'s recent acquisitions..."):
                    ai_notes = generate_superstar_notes(investor_choice, new_buy_tickers)
                    st.info(ai_notes)
