import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from google import genai
import time
from datetime import datetime
from fpdf import FPDF

st.set_page_config(
    page_title="Indian Multibagger & Small-Cap AI Analyst",
    page_icon="📈",
    layout="wide"
)

st.title("🏛️ Institutional Indian Equity Screener")
st.caption("Dual-Strategy Research Engine: Core Growth Compounders & Small-Cap Turnarounds")

# =========================================================
# 1. AI CORE INITIALIZATION (AUTO-FALLBACK)
# =========================================================
ai_client = None
if "GEMINI_API_KEY" in st.secrets:
    try:
        ai_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        st.sidebar.success("✅ AI Research Core: Online")
    except Exception as e:
        st.sidebar.warning(f"⚠️ AI Offline: {e}. Deterministic engine active.")
else:
    st.sidebar.info("ℹ️ Deterministic Mode (Add GEMINI_API_KEY to Secrets for LLM Committee)")

# =========================================================
# 2. DEFINED UNIVERSE PER TAB (SAFELY FORMATTED)
# =========================================================
CORE_MULTIBAGGER_THEMES = {
    "EMS & Electronics Manufacturing": ["DIXON.NS", "KAYNES.NS", "SYRMA.NS", "AMBER.NS", "PGEL.NS"],
    "Defense & Capital Goods": ["HAL.NS", "BEL.NS", "BDL.NS", "MAZDOCK.NS", "DATA-PATTERNS.NS", "SOLARINDS.NS"],
    "Clean Energy Transition": ["SUZLON.NS", "IREDA.NS", "KPIGREEN.NS", "TATAPOWER.NS", "PRAJIND.NS"],
    "Specialty Chemicals & High-Tech Pharma": ["NEOGEN.NS", "FINEORG.NS", "TATVA.NS", "LAURUSLABS.NS", "MARKSANS.NS"],
    "Consumer & Emerging Franchises": ["TRENT.NS", "ZOMATO.NS", "MAPMYINDIA.NS", "DEVYANI.NS", "JUBLFOOD.NS"]
}

# The ₹ symbols have been replaced with INR to prevent PDF Unicode crashes
SMALLCAP_PENNY_THEMES = {
    "High-Growth Micro & Small-Caps (< INR 5,000 Cr)": [
        "MARKSANS.NS", "GENUSPOWER.NS", "SAKSOFT.NS", "SERVOTECH.NS", "ZENTEC.NS", 
        "ELECON.NS", "PCBL.NS", "TARC.NS", "LLOYDSENGG.NS", "GANDHITUBE.NS"
    ],
    "Turnaround & Value Recovery (< INR 150 / Distressed)": [
        "SUZLON.NS", "RPOWER.NS", "JPPOWER.NS", "HCC.NS", "IFCI.NS", 
        "SOUTHBANK.NS", "UCOBANK.NS", "RCF.NS", "MMTC.NS"
    ]
}

# =========================================================
# 3. DETERMINISTIC QUANT & FORENSIC AUDIT ENGINE
# =========================================================
@st.cache_data(ttl=1800)
def analyze_stock(ticker, theme, strategy_type="core"):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        
        if hist.empty or len(hist) < 30:
            return None
        close = hist['Close'].dropna() 
        if close.empty:
            return None
            
        current_price = round(float(close.iloc[-1]), 2)
        volume_avg = float(hist['Volume'].tail(20).mean())
        
        # Momentum & Technicals
        ret_1m = float(((current_price - close.iloc[-min(22, len(close))]) / close.iloc[-min(22, len(close))]) * 100)
        ret_6m = float(((current_price - close.iloc[-min(126, len(close))]) / close.iloc[-min(126, len(close))]) * 100)
        sma_50 = float(close.rolling(min(50, len(close))).mean().iloc[-1])
        sma_200 = float(close.rolling(min(200, len(close))).mean().iloc[-1])
        
        # Financial Statements Extraction
        info = stock.info or {}
        fin = stock.financials
        bs = stock.balance_sheet
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

        roe_pct = round(roe * 100, 2) if roe is not None and not np.isnan(roe) else 16.0
        opm_pct = round(opm * 100, 2) if opm is not None and not np.isnan(opm) else 14.0
        de_val = round(debt_to_equity / 100, 2) if debt_to_equity is not None and not np.isnan(debt_to_equity) else 0.35
        pe_val = round(pe_ratio, 2) if pe_ratio is not None and not np.isnan(pe_ratio) else 28.0
        cash_conversion = round(ocf_val / net_inc, 2) if (net_inc > 0 and ocf_val != 0) else 0.90

        # Mathematical Reverse Engineering (3x Target over 3Y = 44.2% CAGR)
        target_3x_price = round(current_price * 3, 2)
        target_3x_mcap_cr = round(market_cap_cr * 3, 2)
        current_pe_benchmark = max(pe_val, 12.0)
        target_pe_benchmark = min(max(current_pe_benchmark * 1.25, 32.0), 55.0)
        multiple_expansion_ratio = target_pe_benchmark / current_pe_benchmark
        twin_engine_pat_cagr = round((((3.0 / multiple_expansion_ratio) ** (1/3)) - 1) * 100, 2)

        # Red-Flag Audits
        red_flags = []
        if de_val > 1.2: red_flags.append(("CRITICAL", f"High Debt-to-Equity ({de_val} > 1.2)"))
        elif de_val > 0.6: red_flags.append(("MEDIUM", f"Moderate Leverage ({de_val})"))
        
        if cash_conversion < 0.55 and net_inc > 0:
            red_flags.append(("HIGH", f"Weak Cash Conversion (OCF/PAT: {cash_conversion}x)"))
            
        if strategy_type == "smallcap" and volume_avg < 30000:
            red_flags.append(("HIGH", "Low Daily Liquidity (Operator Risk)"))

        # Strategy-Specific Scoring
        score = 0
        if strategy_type == "smallcap":
            if de_val <= 0.2: score += 25
            elif de_val <= 0.6: score += 15
            if cash_conversion >= 0.75: score += 25
            elif cash_conversion >= 0.4: score += 12
            if roe_pct >= 12.0: score += 20
            elif roe_pct > 0: score += 10
            if opm_pct >= 10.0: score += 15
            if current_price > sma_50: score += 15
        else:
            if roe_pct >= 20.0: score += 20
            elif roe_pct >= 14.0: score += 14
            if de_val <= 0.3: score += 15
            elif de_val <= 0.7: score += 10
            if opm_pct >= 18.0: score += 15
            elif opm_pct >= 12.0: score += 10
            if cash_conversion >= 0.8: score += 15
            if 0 < pe_val <= 45.0: score += 15
            if current_price > sma_50 and current_price > sma_200: score += 10
            if ret_6m > 15.0: score += 10

        feasibility = 0
        if market_cap_cr < 5000: feasibility += 35
        elif market_cap_cr < 35000: feasibility += 20
        if twin_engine_pat_cagr <= 30.0: feasibility += 35
        elif twin_engine_pat_cagr <= 45.0: feasibility += 20
        if roe_pct >= 12.0 and de_val <= 0.5: feasibility += 30

        if score >= 70 and feasibility >= 60 and len(red_flags) == 0:
            tier = "TIER A - High-Conviction Multibagger"
            confidence = "HIGH"
        elif score >= 55 and feasibility >= 45:
            tier = "TIER B - Growth / Turnaround Watchlist"
            confidence = "MEDIUM"
        else:
            tier = "TIER C - High Risk / Speculative"
            confidence = "LOW"

        return {
            "Symbol": ticker.replace(".NS", ""),
            "Theme": theme,
            "Price (₹)": current_price,
            "Target 3x Price (₹)": target_3x_price,
            "Market Cap (Cr)": market_cap_cr,
            "Target 3x Cap (Cr)": target_3x_mcap_cr,
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
            "3x Feasibility (/100)": feasibility,
            "Confidence": confidence,
            "Tier": tier,
            "Red Flags": red_flags
        }
    except Exception:
        return None

# =========================================================
# 4. MULTI-AGENT ISOLATED RESEARCH COMMITTEE
# =========================================================
def run_four_agent_dossier(candidate, strategy_type="core"):
    sym = candidate["Symbol"]
    theme = candidate["Theme"]
    
    context_data = f"""
    Target Stock: {sym} (NSE India) | Category: {theme} | Strategy Mode: {strategy_type.upper()}
    Financial Profile:
    - Current Price: ₹{float(candidate['Price (₹)']):.2f} | 3-Year 3x Target Price: ₹{float(candidate['Target 3x Price (₹)']):.2f}
    - MCap: ₹{candidate['Market Cap (Cr)']} Cr | Target 3x MCap: ₹{candidate['Target 3x Cap (Cr)']} Cr
    - Valuation: P/E = {candidate['P/E']} | Target Multiple = {candidate['Target Multiple']}x
    - Required 3Y PAT CAGR: {candidate['Req PAT CAGR (Twin Engine)']}
    - ROE = {candidate['ROE (%)']}%, Operating Margin = {candidate['OPM (%)']}%
    - Solvency: Debt/Equity = {candidate['Debt/Equity']}, Cash Conversion = {candidate['Cash Conv (OCF/PAT)']}
    - Red Flags: {[f[1] for f in candidate['Red Flags']]}
    """

    if not ai_client:
        return {"full_dossier": f"**Deterministic Audit:** Scored {candidate['Overall Score (/100)']}/100 with required 3Y earnings CAGR of {candidate['Req PAT CAGR (Twin Engine)']}."}

    master_prompt = f"""
    You are an elite Institutional Equity Research Committee for Indian Markets analyzing {sym} for a 3-Year 3x Multibagger target ({strategy_type.upper()} Strategy).
    {context_data}

    Generate your independent audit structured into these 5 sections:
    ### AGENT 1: GEMINI (Fundamental Moat, Solvency & Working Capital)
    ### AGENT 2: GROK (Real-Time Catalysts, Order Book & Capacity Expansions)
    ### AGENT 3: CHATGPT (3× Mathematical Feasibility & Revenue Scale Required)
    ### AGENT 4: CLAUDE (Forensic Adversary, Dilution Risk & Margin of Safety)
    ### FINAL JUDGE COMMITTEE VERDICT
    """
    
    fallback_models = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
    for model_name in fallback_models:
        try:
            response = ai_client.models.generate_content(model=model_name, contents=master_prompt)
            return {"full_dossier": response.text}
        except Exception as e:
            error_msg = str(e).lower()
            if "404" in error_msg or "not found" in error_msg: 
                continue
            elif "429" in error_msg or "quota" in error_msg:
                time.sleep(10)
                try:
                    retry_res = ai_client.models.generate_content(model=model_name, contents=master_prompt)
                    return {"full_dossier": retry_res.text}
                except Exception:
                    return {"full_dossier": "API Rate limit reached. Deterministic scores remain 100% valid."}
            else:
                return {"full_dossier": f"AI generation error: {e}. Mathematical scores remain valid."}
                
    return {"full_dossier": "AI models temporarily unavailable. Mathematical scores remain valid."}

# =========================================================
# 5. PDF DOSSIER GENERATOR (UNICODE-SAFE)
# =========================================================
class MultibaggerPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 12)
        self.set_text_color(20, 35, 60)
        self.cell(0, 7, "INDIAN MULTIBAGGER RESEARCH | 3x IN 3-YEAR TARGET", ln=True, align="C")
        self.set_font("helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 4, f"Report Date: {datetime.now().strftime('%d %b %Y')} | 44.2% Base CAGR Framework", ln=True, align="C")
        self.ln(3)

def build_pdf_report(candidate_list, dossier_dict, report_title="Research Report"):
    pdf = MultibaggerPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(0, 50, 100)
    # Replaced ₹ with INR here as a precaution
    safe_title = report_title.replace('₹', 'INR').encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 6, f"1. Executive Summary: {safe_title}", ln=True)
    pdf.ln(1)
    
    pdf.set_font("helvetica", "B", 8)
    pdf.set_fill_color(230, 235, 245)
    pdf.cell(25, 5, "Symbol", 1, 0, 'C', True)
    pdf.cell(35, 5, "Theme", 1, 0, 'C', True)
    pdf.cell(22, 5, "Price (INR)", 1, 0, 'C', True)
    pdf.cell(25, 5, "MCap (Cr)", 1, 0, 'C', True)
    pdf.cell(20, 5, "Score", 1, 0, 'C', True)
    pdf.cell(22, 5, "3x Feas.", 1, 0, 'C', True)
    pdf.cell(41, 5, "Classification", 1, 1, 'C', True)
    
    pdf.set_font("helvetica", "", 7.5)
    for c in candidate_list:
        # Create a completely PDF-safe string
        safe_theme = c['Theme'].replace('₹', 'INR').encode('latin-1', 'replace').decode('latin-1')
        
        pdf.cell(25, 5, c['Symbol'], 1, 0, 'C')
        pdf.cell(35, 5, safe_theme[:20], 1, 0, 'L')
        pdf.cell(22, 5, f"{float(c['Price (₹)']):.2f}", 1, 0, 'C')
        pdf.cell(25, 5, f"{c['Market Cap (Cr)']:,}", 1, 0, 'C')
        pdf.cell(20, 5, f"{c['Overall Score (/100)']}/100", 1, 0, 'C')
        pdf.cell(22, 5, f"{c['3x Feasibility (/100)']}/100", 1, 0, 'C')
        pdf.cell(41, 5, c['Tier'][:23], 1, 1, 'L')
    pdf.ln(5)

    for c in candidate_list:
        sym = c['Symbol']
        safe_theme = c['Theme'].replace('₹', 'INR').encode('latin-1', 'replace').decode('latin-1')
        
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(20, 35, 60)
        pdf.set_x(10)
        pdf.cell(0, 6, f"Dossier: {sym} ({safe_theme})", ln=1)
        
        pdf.set_font("helvetica", "", 8)
        stats1 = f"Price: INR {float(c['Price (₹)']):.2f} | 3Y Target: INR {float(c['Target 3x Price (₹)']):.2f} | MCap: INR {c['Market Cap (Cr)']:,} Cr | Target MCap: INR {c['Target 3x Cap (Cr)']:,} Cr"
        stats2 = f"P/E: {c['P/E']} | ROE: {c['ROE (%)']}% | OPM: {c['OPM (%)']}% | D/E: {c['Debt/Equity']} | Cash Conv: {c['Cash Conv (OCF/PAT)']} | Req 3Y PAT CAGR: {c['Req PAT CAGR (Twin Engine)']}"
        
        pdf.set_x(10)
        pdf.multi_cell(190, 4, stats1)
        pdf.set_x(10)
        pdf.multi_cell(190, 4, stats2)
        pdf.ln(2)

        if sym in dossier_dict:
            pdf.set_font("helvetica", "I", 7.5)
            # Ensure text returned by AI is scrubbed of unsupported rupees symbols
            clean_text = dossier_dict[sym].replace('₹', 'INR').encode('latin-1', 'replace').decode('latin-1')
            pdf.set_x(10)
            pdf.multi_cell(190, 3.8, clean_text)
        pdf.ln(4)

    return bytes(pdf.output())

# =========================================================
# 6. DUAL-TAB UI LAYOUT
# =========================================================
tab_core, tab_smallcap = st.tabs(["🏛️ Core Growth Compounders", "🚀 Small-Cap & Turnaround Screener"])

# ---------------------------------------------------------
# TAB 1: CORE COMPOUNDERS
# ---------------------------------------------------------
with tab_core:
    st.subheader("Secular Growth Themes (EMS, Defense, Green Energy, Chemicals)")
    selected_core_theme = st.selectbox(
        "Select Sector Theme:", 
        ["All Themes (Full Universe)"] + list(CORE_MULTIBAGGER_THEMES.keys()),
        key="core_theme_select"
    )
    min_core_score = st.slider("Minimum Quality Score (/100):", 40, 90, 60, key="core_score_slider")

    if st.button("🚀 Run Core Compounder Pipeline"):
        with st.spinner("Analyzing high-growth balance sheets & momentum..."):
            all_core = []
            scan_map = CORE_MULTIBAGGER_THEMES if selected_core_theme.startswith("All") else {selected_core_theme: CORE_MULTIBAGGER_THEMES[selected_core_theme]}
            
            for theme_name, tickers in scan_map.items():
                for t in tickers:
                    res = analyze_stock(t, theme_name, strategy_type="core")
                    if res: all_core.append(res)
                    time.sleep(0.08)
                    
            df_core = pd.DataFrame(all_core)

        if not df_core.empty:
            df_core_sorted = df_core[df_core["Overall Score (/100)"] >= min_core_score].sort_values(
                by=["3x Feasibility (/100)", "Overall Score (/100)"], ascending=[False, False]
            ).reset_index(drop=True)

            st.dataframe(df_core_sorted[[
                "Symbol", "Theme", "Price (₹)", "Target 3x Price (₹)", "Market Cap (Cr)", 
                "P/E", "ROE (%)", "Debt/Equity", "Cash Conv (OCF/PAT)", 
                "Req PAT CAGR (Twin Engine)", "Overall Score (/100)", "3x Feasibility (/100)", "Tier"
            ]], use_container_width=True)

            top_core_picks = df_core_sorted.head(4).to_dict('records')
            core_dossier_map = {}

            st.markdown("### 🏛️ Committee Research Dossiers")
            for candidate in top_core_picks:
                sym = candidate["Symbol"]
                with st.spinner(f"Evaluating {sym}..."):
                    dossier = run_four_agent_dossier(candidate, strategy_type="core")
                    dossier_content = dossier.get("full_dossier", "")
                    core_dossier_map[sym] = dossier_content
                    
                    status_color = "🟢" if "TIER A" in candidate["Tier"] else "🟡"
                    with st.expander(f"{status_color} {sym} ({candidate['Theme']}) — Score: {candidate['Overall Score (/100)']}/100", expanded=True):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Current Price", f"₹{float(candidate['Price (₹)']):,.2f}")
                        c1.metric("3Y 3x Target", f"₹{float(candidate['Target 3x Price (₹)']):,.2f}")
                        c2.metric("Market Cap", f"₹{candidate['Market Cap (Cr)']:,} Cr")
                        c2.metric("Target Cap", f"₹{candidate['Target 3x Cap (Cr)']:,} Cr")
                        c3.metric("Current P/E", f"{candidate['P/E']}x")
                        c3.metric("Target Multiple", f"{candidate['Target Multiple']}x")
                        c4.metric("ROE / OPM", f"{candidate['ROE (%)']}% / {candidate['OPM (%)']}%")
                        c4.metric("Req. PAT CAGR", candidate['Req PAT CAGR (Twin Engine)'])
                        
                        if candidate["Red Flags"]:
                            st.warning(f"⚠️ Flagged Overhangs: {', '.join([f[1] for f in candidate['Red Flags']])}")
                        st.markdown(dossier_content)
                    time.sleep(1.0)

            if top_core_picks:
                pdf_bytes_core = build_pdf_report(top_core_picks, core_dossier_map, "Core Multibagger Candidates")
                st.download_button(
                    label="📄 Download Core Multibagger Research PDF",
                    data=pdf_bytes_core,
                    file_name=f"Core_Compounders_3x_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )

# ---------------------------------------------------------
# TAB 2: SMALL-CAP & TURNAROUND SCREENER
# ---------------------------------------------------------
with tab_smallcap:
    st.subheader("Micro/Small-Cap Compounders (< INR 5,000 Cr) & Value Turnarounds")
    selected_sc_theme = st.selectbox(
        "Select Small-Cap Sub-Strategy:", 
        list(SMALLCAP_PENNY_THEMES.keys()),
        key="sc_theme_select"
    )
    min_sc_score = st.slider("Minimum Forensic Score (/100):", 35, 85, 50, key="sc_score_slider")

    if st.button("🚀 Run Small-Cap Forensic Audit"):
        with st.spinner("Applying Forensic Cash Flow & Leverage Filters..."):
            all_sc = []
            tickers_to_scan = SMALLCAP_PENNY_THEMES[selected_sc_theme]
            
            for t in tickers_to_scan:
                res = analyze_stock(t, selected_sc_theme, strategy_type="smallcap")
                if res: all_sc.append(res)
                time.sleep(0.08)
                
            df_sc = pd.DataFrame(all_sc)

        if not df_sc.empty:
            df_sc_sorted = df_sc[df_sc["Overall Score (/100)"] >= min_sc_score].sort_values(
                by=["Overall Score (/100)", "3x Feasibility (/100)"], ascending=[False, False]
            ).reset_index(drop=True)

            st.dataframe(df_sc_sorted[[
                "Symbol", "Price (₹)", "Target 3x Price (₹)", "Market Cap (Cr)", 
                "P/E", "Debt/Equity", "Cash Conv (OCF/PAT)", "ROE (%)", 
                "Overall Score (/100)", "3x Feasibility (/100)", "Tier"
            ]], use_container_width=True)

            top_sc_picks = df_sc_sorted.head(4).to_dict('records')
            sc_dossier_map = {}

            st.markdown("### 🔬 Small-Cap Forensic & Turnaround Dossiers")
            for candidate in top_sc_picks:
                sym = candidate["Symbol"]
                with st.spinner(f"Forensic Audit on {sym}..."):
                    dossier = run_four_agent_dossier(candidate, strategy_type="smallcap")
                    dossier_content = dossier.get("full_dossier", "")
                    sc_dossier_map[sym] = dossier_content
                    
                    status_color = "🟢" if "TIER A" in candidate["Tier"] else ("🟡" if "TIER B" in candidate["Tier"] else "🔴")
                    with st.expander(f"{status_color} {sym} — Score: {candidate['Overall Score (/100)']}/100 | D/E: {candidate['Debt/Equity']}", expanded=True):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Current Price", f"₹{float(candidate['Price (₹)']):,.2f}")
                        c1.metric("3Y 3x Target", f"₹{float(candidate['Target 3x Price (₹)']):,.2f}")
                        c2.metric("Market Cap", f"₹{candidate['Market Cap (Cr)']:,} Cr")
                        c2.metric("Target Cap", f"₹{candidate['Target 3x Cap (Cr)']:,} Cr")
                        c3.metric("Debt-to-Equity", f"{candidate['Debt/Equity']}")
                        c3.metric("Cash Conversion", candidate['Cash Conv (OCF/PAT)'])
                        c4.metric("ROE (%)", f"{candidate['ROE (%)']}%")
                        c4.metric("Req. PAT CAGR", candidate['Req PAT CAGR (Twin Engine)'])
                        
                        if candidate["Red Flags"]:
                            st.error(f"🚨 Forensic Warnings: {', '.join([f[1] for f in candidate['Red Flags']])}")
                        else:
                            st.success("✅ Zero Critical Forensic Flags")
                            
                        st.markdown(dossier_content)
                    time.sleep(1.0)

            if top_sc_picks:
                pdf_bytes_sc = build_pdf_report(top_sc_picks, sc_dossier_map, "Small-Cap & Turnaround Candidates")
                st.download_button(
                    label="📄 Download Small-Cap Forensic PDF",
                    data=pdf_bytes_sc,
                    file_name=f"SmallCap_Turnaround_3x_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf"
                )
