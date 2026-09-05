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
    page_title="AI Equity Screener",
    page_icon="📈",
    layout="wide"
)

st.title("🏛️ Institutional Indian Equity Screener")
st.caption("AI-Powered Tri-Strategy: Large/Mid-Cap Core | Small-Caps | Penny Stocks")

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
            current_price = float(live_hist['Close'].iloc[-1])
        else:
            current_price = float(hist['Close'].iloc[-1])
            
        if not live_hist.empty and live_hist.index[-1].date() > hist.index[-1].date():
            prev_price = float(hist['Close'].iloc[-1])
        else:
            prev_price = float(hist['Close'].iloc[-2])
            
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
        
        # FIXED: Converted to On-Demand Button so initial page load is instant
        if "nifty_ai_summary" not in st.session_state:
            if st.button("🧠 Generate AI Market Briefing", key="btn_nifty_ai"):
                with st.spinner("Analyzing technical levels..."):
                    st.session_state["nifty_ai_summary"] = generate_ai_sentiment(
                        market_data['price'], market_data['daily_pts'], market_data['daily_pct'], 
                        market_data['ret_1m'], market_data['ret_6m'], market_data['trend']
                    )
                    st.rerun()
        else:
            st.markdown(st.session_state["nifty_ai_summary"])
            
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
# 4. DETERMINISTIC QUANT ENGINE (Parallel Optimized)
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

# =========================================================
# 5. GEMINI DOSSIER GENERATOR
# =========================================================
def run_four_agent_dossier(candidate, strategy_type="core"):
    sym, theme = candidate["Symbol"], candidate["Theme"]
    agent_instructions = """
    ### AGENT 1: GEMINI (Fundamental Moat & Solvency Audit)
    ### AGENT 2: GROK (Operator Manipulation & Order Book)
    ### AGENT 3: CHATGPT (Real Cash Flow Audit)
    ### AGENT 4: CLAUDE (Margin of Safety)
    ### FINAL VERDICT
    """
    context_data = f"""
    Target: {sym} | Theme: {theme} | Strategy: {strategy_type.upper()}
    Price: {candidate['Price (₹)']} | MCap: {candidate['Market Cap (Cr)']}
    ROE: {candidate['ROE (%)']}% | P/E: {candidate['P/E']} | D/E: {candidate['Debt/Equity']}
    Flags: {[f[1] for f in candidate['Red Flags']]}
    """
    
    if not ai_client: return f"**Deterministic Audit:** Scored {candidate['Overall Score (/100)']}/100."

    prompt = f"Analyze {sym}.\n{context_data}\nFormat using standard bullet points (-). NO tables.\nProvide sections:\n{agent_instructions}"
    
    for model_name in ["gemini-3.5-flash", "gemini-3.1-flash-lite"]:
        for attempt in range(2):
            try:
                response = ai_client.models.generate_content(model=model_name, contents=prompt)
                return response.text.strip() if response.text else "Generation failed."
            except Exception as e:
                if "429" in str(e) or "503" in str(e): time.sleep(5)
                else: break
    return "API rate limits reached. Try again shortly."

# =========================================================
# 6. PDF EXPORTER
# =========================================================
class MultibaggerPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 12)
        self.cell(0, 7, "INDIAN EQUITY RESEARCH", ln=True, align="C")
        self.ln(3)

def build_pdf_report(candidate_list, dossier_dict, report_title="Report"):
    pdf = MultibaggerPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(0, 6, f"Summary: {report_title}", ln=True)
    pdf.ln(1)
    
    pdf.set_font("helvetica", "B", 8)
    pdf.set_fill_color(230, 235, 245)
    headers = ["Symbol", "Price", "MCap (Cr)", "Score", "Tier"]
    widths = [25, 25, 30, 20, 50]
    for w, h in zip(widths, headers): pdf.cell(w, 5, h, 1, 0, 'C', True)
    pdf.ln()
    
    pdf.set_font("helvetica", "", 7.5)
    for c in candidate_list:
        pdf.cell(25, 5, c['Symbol'], 1, 0, 'C')
        pdf.cell(25, 5, f"{float(c['Price (₹)']):.2f}", 1, 0, 'C')
        pdf.cell(30, 5, f"{c['Market Cap (Cr)']:,}", 1, 0, 'C')
        pdf.cell(20, 5, f"{c['Overall Score (/100)']}", 1, 0, 'C')
        pdf.cell(50, 5, c['Tier'][:25], 1, 1, 'L')
    pdf.ln(5)

    for c in candidate_list:
        sym = c['Symbol']
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 6, f"Dossier: {sym}", ln=1)
        pdf.set_font("helvetica", "", 8)
        if sym in dossier_dict:
            clean_text = dossier_dict[sym].replace('₹', 'INR').replace('**', '').replace('### ', '')
            pdf.multi_cell(190, 4, clean_text.encode('latin-1', 'ignore').decode('latin-1'))
        pdf.ln(4)
    return pdf.output(dest="S").encode("latin-1")

# =========================================================
# 7. UI WORKFLOW (FAST LAZY LOADING)
# =========================================================
tab_core, tab_smallcap, tab_penny = st.tabs(["🏛️ Large & Mid-Cap Core", "🚀 Small-Caps", "⚠️ Penny & Micro-Caps"])

def render_pipeline_ui(theme_dict, strategy, title, min_score_default):
    st.subheader(title)
    selected_theme = st.selectbox(f"Select Theme:", ["All Themes"] + list(theme_dict.keys()), key=f"sel_{strategy}")
    min_score = st.slider("Minimum Score:", 35, 90, min_score_default, key=f"sld_{strategy}")

    if f"df_{strategy}" not in st.session_state:
        st.session_state[f"df_{strategy}"] = pd.DataFrame()

    if st.button(f"🚀 Run Fast Pipeline", key=f"btn_{strategy}"):
        with st.spinner("Scanning universe using Parallel Processing (much faster)..."):
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
                st.session_state[f"df_{strategy}"] = df[df["Overall Score (/100)"] >= min_score].sort_values(
                    by=["Overall Score (/100)"], ascending=False
                ).reset_index(drop=True)

    df_sorted = st.session_state.get(f"df_{strategy}", pd.DataFrame())
    
    if not df_sorted.empty:
        st.dataframe(df_sorted[["Symbol", "Price (₹)", "Market Cap (Cr)", "P/E", "Debt/Equity", "ROE (%)", "Overall Score (/100)", "Tier"]], use_container_width=True)
        top_picks = df_sorted.head(4).to_dict('records')
        
        st.markdown("### 🔬 Quant Results (Click to generate AI Dossier)")
        dossier_map = {}
        
        for candidate in top_picks:
            sym = candidate["Symbol"]
            color = "🟢" if "TIER A" in candidate["Tier"] else ("🟡" if "TIER B" in candidate["Tier"] else "🔴")
            
            with st.expander(f"{color} {sym} — Quant Score: {candidate['Overall Score (/100)']}/100", expanded=False):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Current Price", f"₹{float(candidate['Price (₹)']):,.2f}")
                c1.metric("Market Cap", f"₹{candidate['Market Cap (Cr)']:,} Cr")
                c2.metric("Debt-to-Equity", f"{candidate['Debt/Equity']}")
                c3.metric("ROE (%)", f"{candidate['ROE (%)']}%")
                c4.metric("3Y 3x Target", f"₹{float(candidate['Target 3x Price (₹)']):,.2f}")
                
                if candidate["Red Flags"]: st.error(f"🚨 Warnings: {', '.join([f[1] for f in candidate['Red Flags']])}")
                
                if f"ai_{sym}" not in st.session_state:
                    if st.button(f"🧠 Generate AI Dossier for {sym}", key=f"gen_{sym}"):
                        with st.spinner("Gemini is writing the dossier..."):
                            st.session_state[f"ai_{sym}"] = run_four_agent_dossier(candidate, strategy)
                            st.rerun()
                else:
                    st.markdown(st.session_state[f"ai_{sym}"])
                    dossier_map[sym] = st.session_state[f"ai_{sym}"]

        if dossier_map:
            pdf = build_pdf_report(top_picks, dossier_map, f"{strategy.capitalize()} Research")
            st.download_button("📄 Download PDF Report", data=pdf, file_name=f"{strategy}_report.pdf", mime="application/pdf", key=f"dl_{strategy}")

with tab_core: render_pipeline_ui(LARGE_MID_CAP_THEMES, "large/mid-cap", "Secular Growth & Market Leaders", 60)
with tab_smallcap: render_pipeline_ui(SMALLCAP_THEMES, "smallcap", "Micro/Small-Cap Compounders", 50)
with tab_penny: render_pipeline_ui(PENNY_MICRO_THEMES, "penny", "High-Risk Penny & Nano-Caps", 50)
