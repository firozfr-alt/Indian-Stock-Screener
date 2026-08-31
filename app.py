import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from google import genai
import time
from datetime import datetime
from fpdf import FPDF

st.set_page_config(
    page_title="Indian Multibagger AI Analyst",
    page_icon="📈",
    layout="wide"
)

st.title("🏛️ Institutional Indian Equity Screener")
st.caption("Tri-Strategy Engine: Core Compounders | Small-Caps | Penny Stocks (Powered exclusively by Google Gemini)")

# =========================================================
# 1. GEMINI AI INITIALIZATION
# =========================================================
ai_client = None
if "GEMINI_API_KEY" in st.secrets:
    try:
        ai_client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        st.sidebar.success("✅ Google Gemini AI: Online (Fortress Mode)")
    except Exception as e:
        st.sidebar.warning(f"⚠️ Gemini Offline: {e}. Deterministic engine active.")
else:
    st.sidebar.info("ℹ️ Deterministic Mode (Add GEMINI_API_KEY to Secrets)")

# =========================================================
# 2. DEFINED UNIVERSES PER TAB
# =========================================================
CORE_MULTIBAGGER_THEMES = {
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
# 3. DETERMINISTIC QUANT & FORENSIC AUDIT ENGINE
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
            if volume_avg < 250000: red_flags.append(("CRITICAL", "Low Liquidity (Operator Trap Risk)"))
            if ocf_val < 0 and net_inc > 0: red_flags.append(("CRITICAL", "Negative OCF with Positive PAT (Fake Earnings Flag)"))
            
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
            if volume_avg < 30000: red_flags.append(("HIGH", "Low Daily Liquidity"))
            if de_val <= 0.2: score += 25
            elif de_val <= 0.6: score += 15
            if cash_conversion >= 0.75: score += 25
            if roe_pct >= 12.0: score += 20
            if opm_pct >= 10.0: score += 15
            if current_price > sma_50: score += 15
            
            if market_cap_cr < 5000: feasibility += 35
            if twin_engine_pat_cagr <= 35.0: feasibility += 35
            if roe_pct >= 12.0 and de_val <= 0.5: feasibility += 30
            
        else: # CORE
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

        if score >= 70 and feasibility >= 60 and len(red_flags) == 0:
            tier = "TIER A - High-Conviction"
        elif score >= 50 and feasibility >= 45:
            tier = "TIER B - Watchlist"
        else:
            tier = "TIER C - Speculative"

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
            "Overall Score (/100)": score,
            "3x Feasibility (/100)": feasibility,
            "Tier": tier,
            "Red Flags": red_flags
        }
    except Exception:
        return None

# =========================================================
# 4. GEMINI FORTRESS RETRY ENGINE
# =========================================================
def run_four_agent_dossier(candidate, strategy_type="core"):
    sym = candidate["Symbol"]
    theme = candidate["Theme"]
    
    agent_instructions = ""
    if strategy_type == "penny":
        agent_instructions = """
        ### AGENT 1: GEMINI (Bankruptcy & Solvency Audit)
        ### AGENT 2: GROK (Operator Manipulation & Volume Analysis)
        ### AGENT 3: CHATGPT (Real Cash Flow vs Fake Earnings Audit)
        ### AGENT 4: CLAUDE (Delisting Risk & Promoter Check)
        ### FINAL JUDGE COMMITTEE VERDICT
        """
    else:
        agent_instructions = """
        ### AGENT 1: GEMINI (Fundamental Moat & Working Capital)
        ### AGENT 2: GROK (Real-Time Catalysts & Order Book)
        ### AGENT 3: CHATGPT (3× Mathematical Feasibility)
        ### AGENT 4: CLAUDE (Forensic Adversary & Margin of Safety)
        ### FINAL JUDGE COMMITTEE VERDICT
        """

    context_data = f"""
    Target: {sym} (NSE India) | Category: {theme} | Strategy: {strategy_type.upper()}
    Price: INR {float(candidate['Price (₹)']):.2f} | MCap: INR {candidate['Market Cap (Cr)']} Cr
    ROE: {candidate['ROE (%)']}% | OPM: {candidate['OPM (%)']}% | P/E: {candidate['P/E']}
    D/E: {candidate['Debt/Equity']} | Cash Conv (OCF/PAT): {candidate['Cash Conv (OCF/PAT)']}
    Flags: {[f[1] for f in candidate['Red Flags']]}
    """

    if not ai_client: 
        return {"full_dossier": f"**Deterministic Audit:** Scored {candidate['Overall Score (/100)']}/100."}

    master_prompt = f"""
    Analyze {sym} ({strategy_type.upper()} Strategy).
    {context_data}
    
    CRITICAL FORMATTING RULES:
    1. NEVER use markdown tables, grid lines, or ASCII art diagrams.
    2. Present all risks, data, and analysis using clean, standard bullet points (-).
    3. Do not use special Unicode characters or emojis.
    
    Provide 5 sections:
    {agent_instructions}
    """
    
    # Google's most reliable and generous free-tier models 
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    
    # Deep Retry System: It will attempt to get a response 3 times per model
    for model_name in models_to_try:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = ai_client.models.generate_content(model=model_name, contents=master_prompt)
                
                if response.text and response.text.strip() != "":
                    return {"full_dossier": response.text.strip()}
                    
            except Exception as e:
                error_str = str(e).lower()
                
                # 1. CATCH RATE LIMITS (429) -> Pause and try this exactly model again
                if "429" in error_str or "quota" in error_str or "exhausted" in error_str or "rate limit" in error_str:
                    time.sleep(20) # A full 20-second pause resets Google's internal RPM tracker
                    continue 
                    
                # 2. CATCH DEAD MODELS (404/400) -> Break the inner loop, move to the next model
                elif "404" in error_str or "not found" in error_str or "invalid" in error_str or "400" in error_str:
                    break 
                    
                # 3. CATCH SAFETY BLOCKS / OTHER -> Move to next model
                else:
                    break
                    
    # If the code reaches this line, every model failed all its retries (Extremely Rare)
    return {"full_dossier": "Gemini API servers are overloaded after multiple retries. Deterministic Math remains 100% valid."}


# =========================================================
# 5. PDF DOSSIER GENERATOR 
# =========================================================
class MultibaggerPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 12)
        self.set_text_color(20, 35, 60)
        self.cell(0, 7, "INDIAN EQUITY RESEARCH DOSSIER", ln=True, align="C")
        self.ln(3)

def build_pdf_report(candidate_list, dossier_dict, report_title="Research Report"):
    pdf = MultibaggerPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    
    pdf.set_font("helvetica", "B", 10)
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
    pdf.cell(22, 5, "Feas.", 1, 0, 'C', True)
    pdf.cell(41, 5, "Classification", 1, 1, 'C', True)
    
    pdf.set_font("helvetica", "", 7.5)
    for c in candidate_list:
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
        pdf.set_x(10)
        pdf.cell(0, 6, f"Dossier: {sym} ({safe_theme})", ln=1)
        
        pdf.set_font("helvetica", "", 8)
        stats1 = f"Price: INR {float(c['Price (₹)']):.2f} | MCap: INR {c['Market Cap (Cr)']:,} Cr | D/E: {c['Debt/Equity']} | Cash Conv: {c['Cash Conv (OCF/PAT)']}"
        pdf.set_x(10)
        pdf.multi_cell(190, 4, stats1)
        pdf.ln(2)

        if sym in dossier_dict:
            pdf.set_font("helvetica", "", 8)
            raw_text = dossier_dict[sym].replace('₹', 'INR').replace('**', '').replace('### ', '').replace('#### ', '')
            clean_text = raw_text.encode('latin-1', 'ignore').decode('latin-1')
            pdf.set_x(10)
            pdf.multi_cell(190, 3.8, clean_text)
        pdf.ln(4)

    return bytes(pdf.output())

# =========================================================
# 6. TRI-TAB UI WORKFLOW 
# =========================================================
tab_core, tab_smallcap, tab_penny = st.tabs(["🏛️ Core Compounders", "🚀 Small-Caps", "⚠️ Penny & Micro-Caps"])

def render_pipeline_ui(theme_dict, strategy, title, min_score_default):
    st.subheader(title)
    selected_theme = st.selectbox(f"Select {strategy.capitalize()} Theme:", ["All Themes"] + list(theme_dict.keys()), key=f"sel_{strategy}")
    min_score = st.slider("Minimum Quality Score (/100):", 35, 90, min_score_default, key=f"sld_{strategy}")

    if st.button(f"🚀 Run {strategy.capitalize()} Pipeline", key=f"btn_{strategy}"):
        with st.spinner("Running Data Audit & Gemini Engine..."):
            all_cands = []
            scan_map = theme_dict if selected_theme.startswith("All") else {selected_theme: theme_dict[selected_theme]}
            
            for t_name, tickers in scan_map.items():
                for t in tickers:
                    res = analyze_stock(t, t_name, strategy_type=strategy)
                    if res: all_cands.append(res)
                    time.sleep(0.05)
                    
            df = pd.DataFrame(all_cands)

        if not df.empty:
            df_sorted = df[df["Overall Score (/100)"] >= min_score].sort_values(
                by=["Overall Score (/100)", "3x Feasibility (/100)"], ascending=[False, False]
            ).reset_index(drop=True)

            st.dataframe(df_sorted[[
                "Symbol", "Price (₹)", "Market Cap (Cr)", "P/E", "Debt/Equity", "Cash Conv (OCF/PAT)", 
                "ROE (%)", "Overall Score (/100)", "Tier"
            ]], use_container_width=True)

            top_picks = df_sorted.head(4).to_dict('records')
            dossier_map = {}

            st.markdown(f"### 🔬 {strategy.capitalize()} Research Dossiers")
            for candidate in top_picks:
                sym = candidate["Symbol"]
                with st.spinner(f"Gemini Audit on {sym}..."):
                    dossier = run_four_agent_dossier(candidate, strategy_type=strategy)
                    content = dossier.get("full_dossier", "")
                    dossier_map[sym] = content
                    
                    color = "🟢" if "TIER A" in candidate["Tier"] else ("🟡" if "TIER B" in candidate["Tier"] else "🔴")
                    with st.expander(f"{color} {sym} — Score: {candidate['Overall Score (/100)']}/100", expanded=True):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Current Price", f"₹{float(candidate['Price (₹)']):,.2f}")
                        c1.metric("Market Cap", f"₹{candidate['Market Cap (Cr)']:,} Cr")
                        c2.metric("Debt-to-Equity", f"{candidate['Debt/Equity']}")
                        c2.metric("Cash Conversion", candidate['Cash Conv (OCF/PAT)'])
                        c3.metric("ROE (%)", f"{candidate['ROE (%)']}%")
                        c3.metric("Req. PAT CAGR", candidate['Req PAT CAGR (Twin Engine)'])
                        c4.metric("3Y 3x Target", f"₹{float(candidate['Target 3x Price (₹)']):,.2f}")
                        c4.metric("Target Cap", f"₹{candidate['Target 3x Cap (Cr)']:,} Cr")
                        
                        if candidate["Red Flags"]:
                            st.error(f"🚨 Warnings: {', '.join([f[1] for f in candidate['Red Flags']])}")
                        else:
                            st.success("✅ Zero Critical Flags")
                        st.markdown(content)
                    
                    # PACE MAKER: A strict 15-second gap between successful stocks keeps you safely under the 15 RPM limit 
                    time.sleep(15.0)

            if top_picks:
                pdf = build_pdf_report(top_picks, dossier_map, f"{strategy.capitalize()} Candidates")
                st.download_button("📄 Download Clean PDF Dossier", data=pdf, file_name=f"{strategy}_research.pdf", mime="application/pdf", key=f"dl_{strategy}")

# Render the 3 Tabs
with tab_core:
    render_pipeline_ui(CORE_MULTIBAGGER_THEMES, "core", "Secular Growth & Market Leaders", 60)
with tab_smallcap:
    render_pipeline_ui(SMALLCAP_THEMES, "smallcap", "Micro/Small-Cap Compounders (INR 1K-5K Cr)", 50)
with tab_penny:
    render_pipeline_ui(PENNY_MICRO_THEMES, "penny", "High-Risk Penny (< INR 50) & Nano-Caps", 50)
