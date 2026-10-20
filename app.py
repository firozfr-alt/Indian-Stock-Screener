import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from google import genai
import time
from datetime import datetime
from fpdf import FPDF
import concurrent.futures
import requests
import xml.etree.ElementTree as ET

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

def generate_ai_content_safe(prompt):
    """Resilient caller using supported modern models and backoff for rate limits."""
    if not ai_client:
        return None
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash"]
    for model_name in models_to_try:
        for attempt in range(3):
            try:
                response = ai_client.models.generate_content(model=model_name, contents=prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "quota" in err_str or "503" in err_str:
                    time.sleep(5)
                elif "404" in err_str:
                    break
                else:
                    break
    return None

# =========================================================
# 2. LIVE MARKET DASHBOARD, BIAS & NEWS
# =========================================================
def calc_pivot_points(high, low, close):
    pivot = (high + low + close) / 3
    r1 = (2 * pivot) - low
    r2 = pivot + (high - low)
    s1 = (2 * pivot) - high
    s2 = pivot - (high - low)
    return {"PP": pivot, "R1": r1, "R2": r2, "S1": s1, "S2": s2}

@st.cache_data(ttl=300)
def fetch_market_dashboard_data():
    data = {}
    
    tickers = {"Nifty 50": "^NSEI", "Bank Nifty": "^NSEBANK"}
    for name, symbol in tickers.items():
        try:
            tk = yf.Ticker(symbol)
            hist = tk.history(period="5d")
            if len(hist) >= 2:
                prev_day = hist.iloc[-2]
                curr_day = hist.iloc[-1]
                pivots = calc_pivot_points(prev_day['High'], prev_day['Low'], prev_day['Close'])
                
                price = curr_day['Close']
                change = price - prev_day['Close']
                pct_change = (change / prev_day['Close']) * 100
                
                bias = "Bullish" if price > pivots['PP'] else "Bearish"
                
                data[name] = {
                    "price": price, "change": change, "pct": pct_change,
                    "bias": bias, "pivots": pivots
                }
        except Exception:
            pass

    sectors = {
        "Nifty IT": "^CNXIT", "Nifty Auto": "^CNXAUTO", "Nifty FMCG": "^CNXFMCG",
        "Nifty Metal": "^CNXMETAL", "Nifty Pharma": "^CNXPHARMA", 
        "Nifty Energy": "^CNXENERGY", "Nifty Realty": "^CNXREALTY", 
        "Nifty PSU Bank": "^CNXPSUBANK", "Nifty Infra": "^CNXINFRA"
    }
    
    sector_perf = []
    for s_name, s_sym in sectors.items():
        try:
            h = yf.Ticker(s_sym).history(period="2d")
            if len(h) >= 2:
                pct = ((h['Close'].iloc[-1] - h['Close'].iloc[-2]) / h['Close'].iloc[-2]) * 100
                sector_perf.append({"Index": s_name, "Change %": pct})
        except Exception:
            pass
            
    if sector_perf:
        sector_perf = sorted(sector_perf, key=lambda x: x["Change %"], reverse=True)
        data["top_indices"] = sector_perf[:5]
        data["worst_indices"] = sector_perf[-5:]
        
    # --- UPDATED: Indian, Global, Govt & Quarterly Results Feeds (with Deduplication & Title Extraction) ---
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        def get_rss(url, limit=3, extract_company=False):
            try:
                resp = requests.get(url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.content)
                    items = []
                    seen = set()
                    for item in root.findall('./channel/item'):
                        raw_title = item.find('title').text
                        link = item.find('link').text
                        if raw_title and raw_title not in seen:
                            seen.add(raw_title)
                            title = raw_title
                            if extract_company:
                                # Strip out the financial metrics to leave just the company name
                                for kw in [" Consolidated", " Standalone", " Q1", " Q2", " Q3", " Q4", " Net Sales", " profit", " earnings"]:
                                    if kw in title:
                                        title = title.split(kw)[0]
                                        break
                            items.append({"title": title.strip(), "link": link.strip()})
                            if len(items) == limit:
                                break
                    return items
            except:
                pass
            return []

        data["news_indian"] = get_rss("https://www.moneycontrol.com/rss/business.xml", 3)
        data["news_global"] = get_rss("https://www.moneycontrol.com/rss/internationalmarkets.xml", 3)
        data["news_govt"] = get_rss("https://www.moneycontrol.com/rss/economy.xml", 3)
        data["news_results"] = get_rss("https://www.moneycontrol.com/rss/results.xml", 5, extract_company=True)
    except Exception:
        pass

    return data

dash_data = fetch_market_dashboard_data()

with st.expander("🌐 LIVE MARKET BIAS & DASHBOARD", expanded=True):
    if dash_data:
        col1, col2 = st.columns(2)
        for idx, (name, key) in enumerate([("Nifty 50", col1), ("Bank Nifty", col2)]):
            if name in dash_data:
                d = dash_data[name]
                color = "green" if d['change'] > 0 else "red"
                bias_color = "green" if d['bias'] == "Bullish" else "red"
                key.markdown(f"### {name}: **<span style='color:{color}'>{d['price']:,.2f} ({d['pct']:+.2f}%)</span>**", unsafe_allow_html=True)
                key.markdown(f"**Market BIAS:** <span style='color:{bias_color}'>{d['bias']}</span> (Relative to Pivot)", unsafe_allow_html=True)
                key.markdown(f"🔺 **Resistance:** R1: {d['pivots']['R1']:,.0f} | R2: {d['pivots']['R2']:,.0f}")
                key.markdown(f"🔻 **Support:** S1: {d['pivots']['S1']:,.0f} | S2: {d['pivots']['S2']:,.0f}")
                
        st.divider()
        col_t, col_w = st.columns(2)
        with col_t:
            st.markdown("#### 🏆 Top 5 Performing Indices")
            if "top_indices" in dash_data:
                for idx in dash_data["top_indices"]:
                    st.write(f"🟢 **{idx['Index']}**: {idx['Change %']:+.2f}%")
                    
        with col_w:
            st.markdown("#### 📉 Worst 5 Performing Indices")
            if "worst_indices" in dash_data:
                for idx in dash_data["worst_indices"]:
                    st.write(f"🔴 **{idx['Index']}**: {idx['Change %']:+.2f}%")
                    
        st.divider()
        st.markdown("#### 📰 Major Market Updates & Corporate Actions")
        
        col_n1, col_n2 = st.columns(2)
        
        with col_n1:
            st.markdown("##### 🇮🇳 Indian Market News")
            if "news_indian" in dash_data and dash_data["news_indian"]:
                for n in dash_data["news_indian"]: st.markdown(f"▪️ [{n['title']}]({n['link']})")
            else:
                st.write("Feed unavailable.")
                
            st.markdown("##### 🌍 Global Market News")
            if "news_global" in dash_data and dash_data["news_global"]:
                for n in dash_data["news_global"]: st.markdown(f"▪️ [{n['title']}]({n['link']})")
            else:
                st.write("Feed unavailable.")

        with col_n2:
            st.markdown("##### 🏛️ Govt Announcements & Economy")
            if "news_govt" in dash_data and dash_data["news_govt"]:
                for n in dash_data["news_govt"]: st.markdown(f"▪️ [{n['title']}]({n['link']})")
            else:
                st.write("Feed unavailable.")
                
            st.markdown("##### 📅 Upcoming & Recent Quarterly Results")
            if "news_results" in dash_data and dash_data["news_results"]:
                for n in dash_data["news_results"]: st.markdown(f"▪️ [{n['title']}]({n['link']})")
            else:
                st.write("Feed unavailable.")
    else:
        st.error("Market dashboard data unavailable.")

st.divider()

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

def fetch_dossier_sequential(candidate, strategy):
    sym, theme = candidate["Symbol"], candidate["Theme"]
    if not ai_client: return sym, f"**Deterministic Audit:** Scored {candidate['Overall Score (/100)']}/100."

    prompt = f"""Analyze {sym} (Theme: {theme}, Strategy: {strategy.upper()}).
    Price: {candidate['Price (₹)']} | MCap: {candidate['Market Cap (Cr)']}
    ROE: {candidate['ROE (%)']}% | P/E: {candidate['P/E']} | D/E: {candidate['Debt/Equity']}
    
    Provide brief bullet points for:
    - Fundamental Moat
    - Solvency Audit
    - FINAL VERDICT (BUY/SELL/WATCH/AVOID) and 1-sentence rationale.
    """
    res = generate_ai_content_safe(prompt)
    if res:
        return sym, res
    return sym, f"**Deterministic Audit:** Scored {candidate['Overall Score (/100)']}/100. (AI Rate Throttled)"

# =========================================================
# 5. PDF EXPORTERS
# =========================================================
class MultibaggerPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 12)
        self.cell(0, 7, "INDIAN EQUITY RESEARCH", ln=True, align="C")
        self.ln(3)

def clean_text_for_pdf(text):
    if not isinstance(text, str): text = str(text)
    replacements = {'₹': 'INR ', '—': '-', '–': '-', '’': "'", '‘': "'", '“': '"', '”': '"', '•': '-', '…': '...', '**': '', '### ': '\n'}
    for k, v in replacements.items(): text = text.replace(k, v)
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
# 6. MULTIBAGGER QUANT/TECH ENGINE
# =========================================================
@st.cache_data(ttl=1800)
def evaluate_stock_technicals_and_pattern(ticker):
    try:
        clean_ticker = ticker.replace('.NS', '').replace('.BO', '')
        stock = yf.Ticker(f"{clean_ticker}.NS")
        hist = stock.history(period="1y")
        if hist.empty or len(hist) < 50: return None
        
        close = hist['Close'].dropna()
        volume = hist['Volume'].dropna()
        current_price = float(close.iloc[-1])
        high_52w = float(close.max())
        avg_vol_20 = float(volume.tail(20).mean())
        latest_vol = float(volume.iloc[-1])
        vol_surge = round(latest_vol / avg_vol_20, 2) if avg_vol_20 > 0 else 1.0

        sma_20 = float(close.rolling(20).mean().iloc[-1])
        sma_50 = float(close.rolling(50).mean().iloc[-1])
        sma_200 = float(close.rolling(min(200, len(close))).mean().iloc[-1])

        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = float(100 - (100 / (1 + rs)).iloc[-1])

        info = stock.info or {}
        market_cap_cr = round(info.get('marketCap', 0) / 10000000, 2)
        if market_cap_cr <= 0:
            market_cap_cr = round((current_price * info.get('sharesOutstanding', 10000000)) / 10000000, 2)
        
        roe = round(info.get('returnOnEquity', 0.12) * 100, 2) if info.get('returnOnEquity') else 12.0
        de_ratio = round(info.get('debtToEquity', 30.0) / 100, 2) if info.get('debtToEquity') else 0.30
        pe_ratio = round(info.get('trailingPE', 25.0), 2) if info.get('trailingPE') else 25.0

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

        passes_multibagger_core = (roe >= 14.0) and (de_ratio <= 0.8) and (market_cap_cr >= 800)

        return {
            "Symbol": clean_ticker, "Price": round(current_price, 2),
            "Market Cap (Cr)": market_cap_cr, "P/E": pe_ratio,
            "ROE (%)": roe, "Debt/Equity": de_ratio, "RSI(14)": round(rsi, 2),
            "SMA 50": round(sma_50, 2), "SMA 200": round(sma_200, 2),
            "Vol Ratio": f"{vol_surge}x", "Setup Pattern": setup_pattern,
            "Multibagger Base": "Pass" if passes_multibagger_core else "Watch",
            "52W High": round(high_52w, 2)
        }
    except Exception:
        return None

def generate_ai_multibagger_verdict(stock_data):
    sym = stock_data["Symbol"]
    pattern = stock_data["Setup Pattern"]
    
    if "Breakout" in pattern and stock_data["ROE (%)"] >= 15 and stock_data["Debt/Equity"] <= 0.5:
        deterministic_verdict = "**[BUY]**\n- Setup: High momentum breakout on low debt & strong capital returns.\n- Target Horizon: 1-2 years."
    elif "Pullback" in pattern and stock_data["Debt/Equity"] <= 0.6:
        deterministic_verdict = "**[BUY]** (Accumulate on Dips)\n- Setup: Healthy pullback to primary 50 SMA support.\n- Target Horizon: 6-12 months."
    elif stock_data["Debt/Equity"] > 1.0:
        deterministic_verdict = "**[AVOID]**\n- Setup: Excessive leverage reduces margin of safety.\n- Target Horizon: None."
    else:
        deterministic_verdict = "**[WATCH]**\n- Setup: Wait for confirmed volume expansion or support test.\n- Target Horizon: Review quarterly."

    if not ai_client:
        return deterministic_verdict

    prompt = f"""
    Evaluate Indian Stock: {sym}
    Market Cap: INR {stock_data['Market Cap (Cr)']} Cr | P/E: {stock_data['P/E']} | ROE: {stock_data['ROE (%)']}% | D/E: {stock_data['Debt/Equity']}
    Price: INR {stock_data['Price']} | 52W High: INR {stock_data['52W High']} | RSI: {stock_data['RSI(14)']} | Setup: {pattern}

    Format exactly:
    Verdict: **[BUY]**, **[SELL]**, **[WATCH]**, or **[AVOID]**
    Setup Quality: [1 sentence on momentum setup]
    Holding Horizon: [Optimal period, e.g. 6-12 months]
    """
    res = generate_ai_content_safe(prompt)
    return res if res else deterministic_verdict

# =========================================================
# 7. SUPERSTAR INVESTORS DATABASE
# =========================================================
@st.cache_data(ttl=3600)
def get_superstar_portfolio(investor_name):
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

def generate_superstar_notes(investor, new_buys):
    if not ai_client: return "Gemini API key is required to generate AI notes."
    if not new_buys: return "No fresh entries or additions detected this quarter."
    
    prompt = f"""
    Top Indian investor {investor} recently made fresh investments or added stakes in: {', '.join(new_buys)}.
    Write a brief analytical note (3-4 sentences maximum) explaining potential fundamental rationale, tailwinds, or catalysts.
    """
    res = generate_ai_content_safe(prompt)
    return res if res else "AI models are currently rate limited. Please try again shortly."

# =========================================================
# 8. MAIN UI TABS & WORKFLOW
# =========================================================
tab_core, tab_smallcap, tab_penny, tab_auto_ai, tab_multibagger, tab_smart_money = st.tabs([
    "🏛️ Large & Mid-Cap Core", "🚀 Small-Caps", "⚠️ Penny & Micro-Caps", "🤖 AI Auto-Screener", "🏆 AI Multibagger Stocks", "🐋 Superstar Smart Money"
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
            
            my_bar = st.progress(0, text="Generating AI Dossiers sequentially (rate limit protection)...")
            for i, cand in enumerate(top_picks):
                sym, content = fetch_dossier_sequential(cand, strategy)
                dossier_map[sym] = content
                my_bar.progress((i + 1) / len(top_picks), text=f"Generated {sym} ({i+1}/{len(top_picks)})")
                time.sleep(3)
            my_bar.empty()

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
# TAB 4: AI AUTO-SCREENER
# =========================================================
with tab_auto_ai:
    st.subheader("🤖 AI Auto-Screener (Cross Market)")
    st.write("Autonomous cross-market scanner for Indian Equities showing momentum and strong fundamentals.")
    
    if st.button("🔍 Launch Deep AI Scan", type="primary"):
        if not ai_client:
            st.error("Gemini API Key is required for this feature.")
        else:
            with st.spinner("AI is analyzing broader market technicals and fundamentally sound companies..."):
                prompt = """
                You are a senior Indian equity quant analyst. Scan the Indian equity universe across NSE and BSE (spanning Large, Mid, Small, Micro, or Penny stocks).
                Select 5 top stocks that currently display:
                1. High relative momentum, technical continuation, or breakout setups.
                2. Solid fundamental backbone (healthy ROE, sustainable leverage, operating margins).

                For each of the 5 stocks, structure your response as:
                - **Stock Name & Ticker**: (e.g. HAL - NSE)
                - **Market Cap Category**: (e.g. Large-Cap / Micro-Cap)
                - **Why it passed the scan**: Detail the exact technical price action reason and fundamental catalyst.
                """
                res = generate_ai_content_safe(prompt)
                if res:
                    st.markdown("### 🎯 AI Screener Results")
                    st.markdown(res)
                else:
                    st.error("AI Scan failed due to API limits. Please wait 30 seconds and try again.")

# =========================================================
# TAB 5: AI MULTIBAGGER STOCKS
# =========================================================
with tab_multibagger:
    st.subheader("🏆 AI-Discovered Multibagger Screener")
    st.caption("AI dynamically hunts for high-growth sectors, extracts candidates, and filters them through strict technical/fundamental checks.")

    col_m1, col_m2, col_m3 = st.columns([2, 1, 1])
    with col_m1:
        pattern_filter = st.selectbox(
            "Filter Setup Pattern:", 
            ["All Setups", "🚀 52W High Breakout", "🎯 Key Support Pullback", "⚡ Trend Momentum Continuation"]
        )
    with col_m2:
        ai_sector_focus = st.selectbox(
            "AI Discovery Theme:",
            ["General High Growth", "Defense & Aerospace", "Green Energy & EV", "EMS & Semi-conductors", "Undervalued Turnarounds"]
        )
    with col_m3:
        st.write("")
        st.write("")
        run_multi_scan = st.button("🤖 Ask AI & Scan", use_container_width=True)

    if run_multi_scan:
        dynamic_watchlist = []
        with st.spinner(f"AI is hunting for {ai_sector_focus} multibagger candidates..."):
            ai_prompt = f"""
            Act as a quantitative Indian equity screener. 
            Identify 12 mid-cap and small-cap Indian stocks listed on the NSE that fit the theme: "{ai_sector_focus}" and have high multibagger potential.
            Return ONLY a comma-separated list of their NSE trading symbols (e.g. RELIANCE, TCS, HAL, KAYNES). 
            Do not include '.NS' and no markdown text.
            """
            res_text = generate_ai_content_safe(ai_prompt)
            if res_text:
                raw_symbols = res_text.strip().replace('\n', '').replace(' ', '').split(',')
                dynamic_watchlist = [sym.upper() for sym in raw_symbols if sym.isalpha()]
            else:
                dynamic_watchlist = ["DIXON", "KAYNES", "HAL", "IREDA", "ZENTEC", "TATAPOWER", "SUZLON", "PCBL"]

        if dynamic_watchlist:
            st.success(f"**Identified Candidates:** {', '.join(dynamic_watchlist)}")
            
            with st.spinner("Analyzing Technicals & Fundamentals..."):
                scanned_records = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                    futures = [executor.submit(evaluate_stock_technicals_and_pattern, sym) for sym in set(dynamic_watchlist)]
                    for future in concurrent.futures.as_completed(futures):
                        res = future.result()
                        if res: scanned_records.append(res)

            if not scanned_records:
                st.error("Market data feed temporarily unavailable for these symbols.")
            else:
                df_screen = pd.DataFrame(scanned_records)
                if pattern_filter != "All Setups":
                    df_screen = df_screen[df_screen["Setup Pattern"] == pattern_filter]

                if df_screen.empty:
                    st.warning(f"None of the candidates currently qualify for {pattern_filter}. Showing all setups.")
                    df_screen = pd.DataFrame(scanned_records)

                df_screen = df_screen.sort_values(by=["RSI(14)", "ROE (%)"], ascending=[False, False]).reset_index(drop=True)
                st.dataframe(df_screen[["Symbol", "Price", "Setup Pattern", "RSI(14)", "Vol Ratio", "ROE (%)", "Debt/Equity", "P/E", "Multibagger Base"]], use_container_width=True)

                st.markdown("### 🤖 Institutional AI Verdict & Trade Horizons")
                top_candidates = df_screen.head(4).to_dict("records")
                
                for cand in top_candidates:
                    sym = cand["Symbol"]
                    pattern = cand["Setup Pattern"]
                    verdict_text = generate_ai_multibagger_verdict(cand)
                    with st.expander(f"{pattern} — {sym} (Price: ₹{cand['Price']:,} | RSI: {cand['RSI(14)']})", expanded=True):
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Current Price", f"₹{cand['Price']:,.2f}")
                        c2.metric("Setup", cand["Setup Pattern"])
                        c3.metric("ROE / Debt-to-Equity", f"{cand['ROE (%)']}% / {cand['Debt/Equity']}")
                        c4.metric("Volume Surge", cand["Vol Ratio"])
                        st.markdown(verdict_text)
                    time.sleep(2)

# =========================================================
# TAB 6: SUPERSTAR SMART MONEY
# =========================================================
with tab_smart_money:
    st.subheader("🐋 Whale Tracker: Top 10 Superstar Investors' Holdings")
    st.write("Tracks recent block deals and quarterly shareholding patterns for India's biggest investors.")
    
    top_10_investors = [
        "Radhakishan Damani", "Rekha Jhunjhunwala", "Mukul Agrawal", 
        "Ashish Kacholia", "Akash Bhanshali", "Vijay Kedia", 
        "Porinju V Veliyath", "Dolly Khanna", "Anil Kumar Goel", "Ashish Dhawan"
    ]
    
    investor_choice = st.selectbox("Select Superstar Investor:", top_10_investors)
    
    if st.button(f"Load {investor_choice} Portfolio"):
        with st.spinner(f"Loading filings for {investor_choice}..."):
            portfolio_df = get_superstar_portfolio(investor_choice)
            
            st.markdown(f"### {investor_choice}'s Recent Buys & Top Holdings")
            
            def highlight_fresh_buys(row):
                if row['Change (QoQ)'] == 'Fresh Entry' or '+' in row['Change (QoQ)']:
                    return ['background-color: rgba(0, 255, 0, 0.15)'] * len(row)
                return [''] * len(row)
                
            st.dataframe(portfolio_df.style.apply(highlight_fresh_buys, axis=1), use_container_width=True)
            
            new_buys_df = portfolio_df[portfolio_df['Change (QoQ)'].str.contains('Fresh Entry|\\+', case=False, na=False, regex=True)]
            
            if not new_buys_df.empty:
                new_buy_tickers = new_buys_df['Stock'].tolist()
                st.markdown("### 🤖 AI Smart Money Notes on New Buys")
                with st.spinner(f"AI is analyzing {investor_choice}'s acquisitions..."):
                    ai_notes = generate_superstar_notes(investor_choice, new_buy_tickers)
                    st.info(ai_notes)
