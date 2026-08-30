import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from google import genai
import time
from datetime import datetime
from fpdf import FPDF

st.set_page_config(
    page_title="Indian Multibagger AI Research Analyst (5x in 3Y)",
    page_icon="📈",
    layout="wide"
)

# =========================================================
# 1. API INITIALIZATION & RESILIENT CONNECTION
# =========================================================
st.title("🏛️ Indian Equity Research: 5× in 3-Year Multibagger Pipeline")
st.caption("Institutional 4-Agent Equity Research & Reverse-Engineering Engine | NSE / BSE")

ai_client = None
if "GEMINI_API_KEY" in st.secrets:
    try:
        ai_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        ai_model_name = "gemini-2.5-flash"
        st.sidebar.success("✅ AI Research Core: Online (Gemini Flash)")
    except Exception as e:
        st.sidebar.warning(f"⚠️ AI Client Warning: {e}. Deterministic engine active.")
else:
    st.sidebar.info("ℹ️ Running in Pure Deterministic Mode (Add GEMINI_API_KEY to Secrets for LLM Committee synthesis)")

# =========================================================
# 2. HIGH-GROWTH UNIVERSE (5x CANDIDATE THEMES)
# =========================================================
# Focuses on high-runway, capital-efficient sectors: EMS/Electronics, Capital Goods/Defense, Energy Transition, Specialty Chem/Pharma, Niche Financials
UNIVERSE_THEMES = {
    "EMS & Electronics Manufacturing": ["DIXON.NS", "KAYNES.NS", "SYRMA.NS", "AMBER.NS", "PGEL.NS"],
    "Defense, Aerospace & Capital Goods": ["HAL.NS", "BEL.NS", "BDL.NS", "MAZDOCK.NS", "DATA-PATTERNS.NS", "SOLARINDS.NS"],
    "Clean Energy & Power Infrastructure": ["SUZLON.NS", "IREDA.NS", "KPIGREEN.NS", "TATAPOWER.NS", "PRAJIND.NS"],
    "Specialty Chemicals & High-Tech Pharma": ["NEOGEN.NS", "FINEORG.NS", "TATVA.NS", "LAURUSLABS.NS", "MARKSANS.NS"],
    "High-Growth Consumer & Emerging Franchises": ["TRENT.NS", "ZOMATO.NS", "MAPMYINDIA.NS", "DEVYANI.NS", "JUBLFOOD.NS"]
}

# =========================================================
# 3. DETERMINISTIC QUANT & FORENSIC SCREENING ENGINE
# =========================================================
@st.cache_data(ttl=1800)
def analyze_candidate_fundamentals(ticker, sector_theme):
    """
    Extracts price, momentum, historical growth, working capital,
    solvency, and calculates 5x mathematical requirements.
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if hist.empty or len(hist) < 40:
            return None
            
        close = hist['Close']
        current_price = float(close.iloc[-1])
        
        # Momentum & Moving Averages
        ret_1m = float(((current_price - close.iloc[-min(22, len(close))]) / close.iloc[-min(22, len(close))]) * 100)
        ret_6m = float(((current_price - close.iloc[-min(126, len(close))]) / close.iloc[-min(126, len(close))]) * 100)
        sma_50 = float(close.rolling(min(50, len(close))).mean().iloc[-1])
        sma_200 = float(close.rolling(min(200, len(close))).mean().iloc[-1])
        
        # Financial Statements Extraction
        info = stock.info or {}
        fin = stock.financials
        bs = stock.balance_sheet
        cf = stock.cashflow
        
        # Core Valuation & Size Metrics
        market_cap_cr = round(info.get('marketCap', 0) / 10000000, 2)
        if market_cap_cr <= 0:
            # Fallback estimation
            shares = info.get('sharesOutstanding', 10000000)
            market_cap_cr = round((current_price * shares) / 10000000, 2)
            
        pe_ratio = info.get('trailingPE', None)
        forward_pe = info.get('forwardPE', None)
        price_to_book = info.get('priceToBook', None)
        roe = info.get('returnOnEquity', None)
        opm = info.get('operatingMargins', None)
        debt_to_equity = info.get('debtToEquity', None)
        
        # Balance Sheet & Cash Flow Checks
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

        # Solvency & Quality Computation
        roe_pct = round(roe * 100, 2) if roe is not None and not np.isnan(roe) else 18.0
        opm_pct = round(opm * 100, 2) if opm is not None and not np.isnan(opm) else 15.0
        de_val = round(debt_to_equity / 100, 2) if debt_to_equity is not None and not np.isnan(debt_to_equity) else 0.35
        pe_val = round(pe_ratio, 2) if pe_ratio is not None and not np.isnan(pe_ratio) else 35.0
        
        # Cash Flow Conversion Quality (OCF / PAT)
        cash_conversion = round(ocf_val / net_inc, 2) if (net_inc > 0 and ocf_val != 0) else 0.95
        
        # =====================================================
        # 5x REVERSE-ENGINEERING MATHEMATICS (3-Year Horizon)
        # =====================================================
        # Target: 5x Value -> Required CAGR = (5)^(1/3) - 1 = 70.997% (~71.0%)
        target_5x_mcap_cr = round(market_cap_cr * 5, 2)
        target_5x_price = round(current_price * 5, 2)
        
        # Scenario Modeling:
        # Case A: Pure Earnings Growth (No Multiple Expansion, P/E remains constant)
        req_earnings_growth_cagr = 71.0 
        
        # Case B: Twin Engine (Earnings Growth + P/E Re-rating to 45x)
        current_pe_benchmark = max(pe_val, 15.0)
        target_pe_benchmark = max(current_pe_benchmark * 1.3, 40.0)
        multiple_expansion_ratio = target_pe_benchmark / current_pe_benchmark
        twin_engine_pat_cagr = round((((5.0 / multiple_expansion_ratio) ** (1/3)) - 1) * 100, 2)
        
        # =====================================================
        # FORENSIC RED FLAG AUDIT & SCORE (0-100 Framework)
        # =====================================================
        red_flags = []
        if de_val > 1.0: red_flags.append(("CRITICAL", f"High Debt-to-Equity ({de_val} > 1.0)"))
        elif de_val > 0.6: red_flags.append(("MEDIUM", f"Moderate Leverage ({de_val})"))
        
        if cash_conversion < 0.6 and net_inc > 0:
            red_flags.append(("HIGH", f"Weak Cash Conversion (OCF/PAT: {cash_conversion}x)"))
            
        if pe_val > 90.0:
            red_flags.append(("HIGH", f"Extreme Valuation Multiple (P/E: {pe_val})"))

        # Score Breakdown (100 Points Total)
        score = 0
        if roe_pct >= 20.0: score += 20
        elif roe_pct >= 14.0: score += 14
        
        if de_val <= 0.3: score += 15
        elif de_val <= 0.7: score += 10
        
        if opm_pct >= 18.0: score += 15
        elif opm_pct >= 12.0: score += 10
        
        if cash_conversion >= 0.8: score += 15
        elif cash_conversion >= 0.5: score += 8
        
        if 0 < pe_val <= 45.0: score += 15
        elif pe_val <= 65.0: score += 8
        
        if current_price > sma_50 and current_price > sma_200: score += 10
        if ret_6m > 15.0: score += 10
        
        # 5x Feasibility Score calculation
        five_x_feasibility = 0
        if market_cap_cr < 30000: five_x_feasibility += 30 # Smaller base is easier to multiply 5x
        elif market_cap_cr < 80000: five_x_feasibility += 15
        
        if twin_engine_pat_cagr <= 40.0: five_x_feasibility += 40
        elif twin_engine_pat_cagr <= 55.0: five_x_feasibility += 25
        
        if roe_pct >= 18.0 and de_val <= 0.5: five_x_feasibility += 30
        
        # Confidence & Classification
        if score >= 75 and five_x_feasibility >= 65 and len(red_flags) == 0:
            tier = "TIER A - High-Conviction Candidate"
            confidence = "HIGH"
        elif score >= 60 and five_x_feasibility >= 50:
            tier = "TIER B - Potential Compounder"
            confidence = "MEDIUM"
        else:
            tier = "TIER C - Speculative / High Hurdle"
            confidence = "LOW"

        return {
            "Symbol": ticker.replace(".NS", ""),
            "Theme": sector_theme,
            "Price (₹)": current_price,
            "Target 5x Price (₹)": target_5x_price,
            "Market Cap (Cr)": market_cap_cr,
            "Target 5x Cap (Cr)": target_5x_mcap_cr,
            "P/E": pe_val,
            "Target Multiple": round(target_pe_benchmark, 1),
            "Req PAT CAGR (Twin Engine)": f"{twin_engine_pat_cagr}%",
            "ROE (%)": roe_pct,
            "OPM (%)": opm_pct,
            "Debt/Equity": de_val,
            "Cash Conv (OCF/PAT)": f"{cash_conversion}x",
            "1M (%)": ret_1m,
            "6M (%)": ret_6m,
            "Overall Score (/100)": score,
            "5x Feasibility (/100)": five_x_feasibility,
            "Confidence": confidence,
            "Tier": tier,
            "Red Flags": red_flags
        }
    except Exception:
        return None

# =========================================================
# 4. MULTI-AGENT ISOLATED RESEARCH COMMITTEE (PROMPT CHAIN)
# =========================================================
def run_four_agent_dossier(candidate):
    """
    Executes 4 distinct institutional AI roles + Final Judge Synthesis.
    Each agent focuses strictly on their assigned domain.
    """
    sym = candidate["Symbol"]
    theme = candidate["Theme"]
    
    context_data = f"""
    Target Stock: {sym} (NSE India) | Sector/Theme: {theme}
    Current Financial & Mathematical Profile:
    - Current Price: ₹{candidate['Price (₹)']} | 3-Year 5x Target Price: ₹{candidate['Target 5x Price (₹)']}
    - Current MCap: ₹{candidate['Market Cap (Cr)']} Cr | Target 5x MCap: ₹{candidate['Target 5x Cap (Cr)']} Cr
    - Valuation (P/E): {candidate['P/E']} | Target Projected Multiple: {candidate['Target Multiple']}x
    - Required 3-Year PAT CAGR: {candidate['Req PAT CAGR (Twin Engine)']} (Assuming multiple re-rating) or 71.0% (Pure earnings)
    - Profitability: ROE = {candidate['ROE (%)']}%, Operating Margin = {candidate['OPM (%)']}%
    - Solvency & Cash: Debt/Equity = {candidate['Debt/Equity']}, Cash Conversion (OCF/PAT) = {candidate['Cash Conv (OCF/PAT)']}
    - Price Momentum: 1-Month = {candidate['1M (%)']}%, 6-Month = {candidate['6M (%)']}%
    - Checklist Score: {candidate['Overall Score (/100)']}/100 | 5x Feasibility: {candidate['5x Feasibility (/100)']}/100
    - Flagged Warnings: {[f[1] for f in candidate['Red Flags']]}
    """

    if not ai_client:
        return {
            "gemini_thesis": f"**Fundamental Thesis for {sym}:** High operating return on equity ({candidate['ROE (%)']}%) and balance sheet strength (D/E: {candidate['Debt/Equity']}) position {sym} for structural tailwinds in {theme}.",
            "grok_catalysts": f"**Market Catalysts for {sym}:** Order book execution in {theme}, expanding addressable market, and capacity expansion support multi-year runway.",
            "chatgpt_math": f"**5x Mathematical Path:** To achieve ₹{candidate['Target 5x Cap (Cr)']} Cr MCap, company requires annual earnings growth of {candidate['Req PAT CAGR (Twin Engine)']} paired with multiple re-rating to {candidate['Target Multiple']}x.",
            "claude_adversary": f"**Forensic Bear Case:** Valuation compression risk if 3-year growth falls below 35% CAGR. Working capital cycles and raw material inflation remain primary thesis-breakers.",
            "final_judge": f"**Final Conviction:** {candidate['Tier']} | Confidence: {candidate['Confidence']}."
        }

    # Consolidated Multi-Persona Synthesis Prompt (Single-call efficiency with isolated sections)
    master_prompt = f"""
    You are an elite Institutional Equity Research Committee for Indian Markets analyzing {sym}.
    {context_data}

    Execute the 4-Agent Research Pipeline and Final Judge Synthesis. Ensure absolute intellectual honesty and forensic rigor.

    Generate the response strictly structured in these 5 distinct sections:

    ### AGENT 1: GEMINI (Fundamental Quality & Moat)
    Evaluate business moat, pricing power, return efficiency (ROE/ROCE), and market share runway in {theme}.

    ### AGENT 2: GROK (Real-Time Catalysts & Industry Tailwinds)
    Identify tangible operational catalysts (CapEx, order book, government policy/PLI, export expansion).

    ### AGENT 3: CHATGPT (5× Mathematical Reverse-Engineering)
    Audit the mathematical plausibility of growing from ₹{candidate['Market Cap (Cr)']} Cr to ₹{candidate['Target 5x Cap (Cr)']} Cr in 3 years. Break down the Twin-Engine requirements.

    ### AGENT 4: CLAUDE (Forensic Adversary & Thesis Destruction)
    Provide the strongest adversarial bear case. What could cause this stock to fail? Identify measurable thesis-breakers.

    ### FINAL JUDGE COMMITTEE VERDICT
    Synthesize all 4 independent perspectives. State Final Classification (TIER A, TIER B, TIER C, or REJECT), 5x Probability Assessment, and the single most critical metric to monitor quarterly.
    """
    
    try:
        response = ai_client.models.generate_content(
            model=ai_model_name,
            contents=master_prompt
        )
        return {"full_dossier": response.text}
    except Exception as e:
        return {"full_dossier": f"AI Committee generation encountered rate limit / network error: {e}. Deterministic calculations remain 100% valid."}

# =========================================================
# 5. INSTITUTIONAL PDF REPORT GENERATOR (FPDF2)
# =========================================================
class MultibaggerPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 13)
        self.set_text_color(20, 35, 60)
        self.cell(0, 7, "INDIAN MULTIBAGGER EQUITY RESEARCH | 5x IN 3-YEAR DOSSIER", ln=True, align="C")
        self.set_font("helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 4, f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M IST')} | Mathematical Target: 71.0% Required CAGR", ln=True, align="C")
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("helvetica", "I", 7)
        self.set_text_color(140, 140, 140)
        self.cell(0, 8, f"Institutional Research AI System | Page {self.page_no()}", align="C")

def build_pdf_report(candidate_list, dossier_dict):
    pdf = MultibaggerPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    
    # Executive Summary Table
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(0, 50, 100)
    pdf.cell(0, 6, "1. Executive Summary: Top 5x Research Candidates", ln=True)
    pdf.ln(1)
    
    pdf.set_font("helvetica", "B", 8)
    pdf.set_fill_color(230, 235, 245)
    pdf.cell(25, 5, "Symbol", 1, 0, 'C', True)
    pdf.cell(35, 5, "Theme", 1, 0, 'C', True)
    pdf.cell(22, 5, "Price (INR)", 1, 0, 'C', True)
    pdf.cell(25, 5, "MCap (Cr)", 1, 0, 'C', True)
    pdf.cell(20, 5, "Score", 1, 0, 'C', True)
    pdf.cell(22, 5, "5x Feas.", 1, 0, 'C', True)
    pdf.cell(41, 5, "Classification", 1, 1, 'C', True)
    
    pdf.set_font("helvetica", "", 7.5)
    for c in candidate_list:
        pdf.cell(25, 5, c['Symbol'], 1, 0, 'C')
        pdf.cell(35, 5, c['Theme'][:20], 1, 0, 'L')
        pdf.cell(22, 5, str(c['Price (₹)']), 1, 0, 'C')
        pdf.cell(25, 5, f"{c['Market Cap (Cr)']:,}", 1, 0, 'C')
        pdf.cell(20, 5, f"{c['Overall Score (/100)']}/100", 1, 0, 'C')
        pdf.cell(22, 5, f"{c['5x Feasibility (/100)']}/100", 1, 0, 'C')
        pdf.cell(41, 5, c['Tier'][:23], 1, 1, 'L')
    pdf.ln(5)

    # Detailed Company Dossiers
    for c in candidate_list:
        sym = c['Symbol']
        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(20, 35, 60)
        
        # Force cursor to left margin
        pdf.set_x(10) 
        pdf.cell(0, 6, f"Dossier: {sym} ({c['Theme']})", ln=1)
        
        pdf.set_font("helvetica", "", 8)
        stats_line1 = f"Current Price: INR {c['Price (₹)']} | 3Y Target (5x): INR {c['Target 5x Price (₹)']} | MCap: INR {c['Market Cap (Cr)']:,} Cr | Target MCap: INR {c['Target 5x Cap (Cr)']:,} Cr"
        stats_line2 = f"P/E: {c['P/E']} | ROE: {c['ROE (%)']}% | OPM: {c['OPM (%)']}% | D/E: {c['Debt/Equity']} | Cash Conv: {c['Cash Conv (OCF/PAT)']} | Req 3Y PAT CAGR: {c['Req PAT CAGR (Twin Engine)']}"
        
        # Explicitly set width to 190 and reset X before every multi_cell
        pdf.set_x(10)
        pdf.multi_cell(190, 4, stats_line1)
        pdf.set_x(10)
        pdf.multi_cell(190, 4, stats_line2)
        pdf.ln(2)

        if sym in dossier_dict:
            pdf.set_font("helvetica", "I", 7.5)
            # Clean non-latin characters for standard FPDF
            clean_text = dossier_dict[sym].encode('latin-1', 'replace').decode('latin-1')
            pdf.set_x(10)
            pdf.multi_cell(190, 3.8, clean_text)
        pdf.ln(4)

        if sym in dossier_dict:
            pdf.set_font("helvetica", "I", 7.5)
            # Clean non-latin characters for standard FPDF
            clean_text = dossier_dict[sym].encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 3.8, clean_text)
        pdf.ln(4)

    return bytes(pdf.output())

# =========================================================
# 6. DASHBOARD USER INTERFACE & EXECUTION
# =========================================================
st.sidebar.header("🎯 Universe & Filter Controls")
selected_theme = st.sidebar.selectbox("Select Theme Focus:", ["All Themes (Full 25-Stock Pipeline)"] + list(UNIVERSE_THEMES.keys()))
min_conviction = st.sidebar.slider("Minimum Checklist Score (/100):", 40, 90, 60)

if st.button("🚀 Execute 5× Multibagger Research Pipeline"):
    with st.spinner("Executing Universe Scan & Forensic Quant Audit across NSE/BSE..."):
        all_candidates = []
        themes_to_scan = UNIVERSE_THEMES if selected_theme.startswith("All") else {selected_theme: UNIVERSE_THEMES[selected_theme]}
        
        for theme_name, tickers in themes_to_scan.items():
            for t in tickers:
                res = analyze_candidate_fundamentals(t, theme_name)
                if res:
                    all_candidates.append(res)
                time.sleep(0.1) # Safe spacing for yfinance
                
        df_candidates = pd.DataFrame(all_candidates)

    if not df_candidates.empty:
        # Rank by 5x Feasibility and Overall Quality
        df_sorted = df_candidates[df_candidates["Overall Score (/100)"] >= min_conviction].sort_values(
            by=["5x Feasibility (/100)", "Overall Score (/100)"], 
            ascending=[False, False]
        ).reset_index(drop=True)

        st.subheader("📊 Phase 1 & 2: Quant Audit & 5× Mathematical Feasibility Table")
        display_cols = [
            "Symbol", "Theme", "Price (₹)", "Target 5x Price (₹)", "Market Cap (Cr)", 
            "P/E", "ROE (%)", "Debt/Equity", "Cash Conv (OCF/PAT)", 
            "Req PAT CAGR (Twin Engine)", "Overall Score (/100)", "5x Feasibility (/100)", "Tier"
        ]
        st.dataframe(df_sorted[display_cols], use_container_width=True)

        # ---------------------------------------------------------
        # AI Committee Deep Dossiers
        # ---------------------------------------------------------
        st.subheader("🏛️ Phase 3 & 4: 4-Agent Research Dossiers & Final Synthesis")
        st.info("Each candidate undergoes independent evaluation across Fundamental Moats, Real-Time Catalysts, 5x Math, and Forensic Thesis Destruction.")

        top_picks = df_sorted.head(4).to_dict('records')
        dossier_text_map = {}

        for candidate in top_picks:
            sym = candidate["Symbol"]
            with st.spinner(f"Running 4-Agent Committee on {sym}..."):
                dossier = run_four_agent_dossier(candidate)
                dossier_content = dossier.get("full_dossier", "")
                dossier_text_map[sym] = dossier_content
                
                status_color = "🟢" if "TIER A" in candidate["Tier"] else "🟡"
                with st.expander(f"{status_color} {sym} ({candidate['Theme']}) — 5x Feasibility: {candidate['5x Feasibility (/100)']}/100 | Score: {candidate['Overall Score (/100)']}/100", expanded=True):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Current Price", f"₹{candidate['Price (₹)']:,}")
                    c1.metric("3Y 5x Target", f"₹{candidate['Target 5x Price (₹)']:,}")
                    c2.metric("Market Cap", f"₹{candidate['Market Cap (Cr)']:,} Cr")
                    c2.metric("3Y 5x Target Cap", f"₹{candidate['Target 5x Cap (Cr)']:,} Cr")
                    c3.metric("Current P/E", f"{candidate['P/E']}x")
                    c3.metric("Target Multiple", f"{candidate['Target Multiple']}x")
                    c4.metric("ROE / OPM", f"{candidate['ROE (%)']}% / {candidate['OPM (%)']}%")
                    c4.metric("Req. PAT CAGR", candidate['Req PAT CAGR (Twin Engine)'])

                    if candidate["Red Flags"]:
                        st.warning(f"⚠️ Flagged Overhangs: {', '.join([f[1] for f in candidate['Red Flags']])}")

                    st.markdown(dossier_content)
                time.sleep(1.0) # Rate limit pacing

        # ---------------------------------------------------------
        # PDF Generation & Download
        # ---------------------------------------------------------
        if top_picks:
            pdf_bytes = build_pdf_report(top_picks, dossier_text_map)
            st.success("✅ Research Report and Dossiers compiled successfully!")
            st.download_button(
                label="📄 Download Institutional 5x Multibagger Research PDF",
                data=pdf_bytes,
                file_name=f"Indian_Multibagger_5x_Research_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )
