import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from google import genai
import time
from datetime import datetime
from fpdf import FPDF
import concurrent.futures
from tradingview_ta import TA_Handler, Interval, Exchange

st.set_page_config(
    page_title="AI Equity Screener & Fundamental Analyst",
    page_icon="📈",
    layout="wide"
)

st.title("🏛️ Institutional Indian Equity Screener")
st.caption("AI-Powered Tri-Strategy Screener, TradingView Technicals & Smart Money Tracker")

# =========================================================
# 1. API INITIALIZATION (GEMINI)
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
            
        if hist.empty or len(hist) < 22: return None
            
        current_price = float(hist['Close'].dropna().iloc[-1])
        prev_price = float(hist['Close'].dropna().iloc[-2])
            
        daily_change_pts = current_price - prev_price
        daily_change_pct = (daily_change_pts / prev_price) * 100
        
        ret_1m = float(((current_price - hist['Close'].iloc[-22]) / hist['Close'].iloc[-22]) * 100)
        ret_6m = float(((current_price - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100)
        
        market_trend = "Bullish" if ret_1m > 0 and ret_6m > 0 else "Bearish" if ret_1m < 0 and ret_6m < 0 else "Mixed/Consolidating"
        
        return {
            "price": current_price, "daily_pts": daily_change_pts, "daily_pct": daily_change_pct,
            "ret_1m": ret_1m, "ret_6m": ret_6m, "trend": market_trend, "is_etf": is_etf
        }
    except Exception:
        return None

@st.cache_data(ttl=3600)
def generate_ai_sentiment(price, daily_pts, daily_pct, ret_1m, ret_6m, trend):
    if not ai_client: return "Market sentiment AI is currently offline. Please configure GEMINI_API_KEY."
    prompt = f"""
    You are a top-tier Institutional Equity Strategist for the Indian Stock Market. Nifty 50: {price:.2f}.
    Delta: {daily_pts:+.2f} pts ({daily_pct:+.2f}%). 1M: {ret_1m:.2f}%. 6M: {ret_6m:.2f}%. Trend: {trend}.
    Write a 3-section institutional briefing using bullet points:
    **1. Trend Confirmation**
    **2. The Upside (Resistance)**
    **3. The Downside (Support)**
    """
    for model_name in ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.5-flash-lite"]:
        try:
            response = ai_client.models.generate_content(model=model_name, contents=prompt)
            if response and response.text: return response.text.strip()
        except: continue
    return "Market sentiment summary unavailable (API quotas exhausted)."

market_data = fetch_market_data()
header_title = "📊 Current Indian Market Sentiment"
if market_data:
    prefix = "Nifty BeES: " if market_data.get("is_etf") else "Nifty 50: "
    header_title = f"📊 Current Indian Market Sentiment ({prefix}₹{market_data['price']:,.2f} | {market_data['daily_pts']:+,.2f} pts / {market_data['daily_pct']:+.2f}%)"

with st.expander(header_title, expanded=True):
    if market_data:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Nifty 50 Proxy", f"₹{market_data['price']:,.2f}", f"{market_data['daily_pts']:+,.2f} ({market_data['daily_pct']:+.2f}%)")
        m2.metric("1-Month Momentum", f"{market_data['ret_1m']:+.2f}%")
        m3.metric("6-Month Momentum", f"{market_data['ret_6m']:+.2f}%")
        m4.metric("Quant Trend", market_data['trend'])
        st.divider()
        with st.spinner("Analyzing technical levels..."):
            st.markdown(generate_ai_sentiment(
                market_data['price'], market_data['daily_pts'], market_data['daily_pct'], 
                market_data['ret_1m'], market_data['ret_6m'], market_data['trend']
            ))


# =========================================================
# 3. DETERMINISTIC QUANT ENGINE (TABS 1-3)
# =========================================================
@st.cache_data(ttl=1800)
def analyze_stock(ticker, theme, strategy_type="core"):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if hist.empty or len(hist) < 30: return None
            
        close = hist['Close'].dropna() 
        current_price = round(float(close.iloc[-1]), 2)
        
        info = stock.info or {}
        market_cap_cr = round(info.get('marketCap', 0) / 10000000, 2)
        if market_cap_cr <= 0: market_cap_cr = round((current_price * info.get('sharesOutstanding', 10000000)) / 10000000, 2)
            
        pe_val = info.get('trailingPE', 25.0)
        roe_pct = round(info.get('returnOnEquity', 0.10) * 100, 2) if info.get('returnOnEquity') else 10.0
        de_val = round(info.get('debtToEquity', 35.0) / 100, 2) if info.get('debtToEquity') else 0.35
        
        # Native TradingView Integration
        tv_rsi = 50.0
        try:
            handler = TA_Handler(symbol=ticker.replace('.NS', ''), screener="india", exchange="NSE", interval=Interval.INTERVAL_1_DAY)
            tv_rsi = handler.get_analysis().indicators.get('RSI', 50.0)
        except: pass
        
        score = 0
        red_flags = []
        if de_val > 1.2: red_flags.append(("CRITICAL", f"High Debt ({de_val})"))
        if tv_rsi > 60: score += 15
        if roe_pct >= 15.0: score += 20
        if de_val <= 0.3: score += 20
        
        tier = "TIER A - High-Conviction" if (score >= 40 and not red_flags) else "TIER B - Watchlist"
        return {
            "Symbol": ticker.replace(".NS", ""), "Theme": theme, "Price (₹)": current_price,
            "Market Cap (Cr)": market_cap_cr, "P/E": pe_val, "ROE (%)": roe_pct, "Debt/Equity": de_val,
            "TV RSI(14)": round(tv_rsi, 2), "Overall Score (/100)": score, "Tier": tier, "Red Flags": red_flags
        }
    except Exception:
        return None


# =========================================================
# 4. TAB 4: TECHNICAL, MOMENTUM & BREAKOUT ENGINE
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

        sma_50 = float(close.rolling(50).mean().iloc[-1])
        sma_200 = float(close.rolling(min(200, len(close))).mean().iloc[-1])

        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = float(100 - (100 / (1 + rs)).iloc[-1])

        info = stock.info or {}
        market_cap_cr = round(info.get('marketCap', 0) / 10000000, 2)
        if market_cap_cr <= 0: market_cap_cr = round((current_price * info.get('sharesOutstanding', 10000000)) / 10000000, 2)
        
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
            "Symbol": clean_ticker, "Price": round(current_price, 2), "Market Cap (Cr)": market_cap_cr,
            "P/E": pe_ratio, "ROE (%)": roe, "Debt/Equity": de_ratio, "RSI(14)": round(rsi, 2),
            "SMA 50": round(sma_50, 2), "SMA 200": round(sma_200, 2), "Vol Ratio": f"{vol_surge}x",
            "Setup Pattern": setup_pattern, "Multibagger Base": "Pass" if passes_multibagger_core else "Watch",
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
        deterministic_verdict = "**[AVOID]**\n- Setup: Excessive leverage reduces risk-adjusted margin of safety.\n- Target Horizon: None."
    else:
        deterministic_verdict = "**[WATCH]**\n- Setup: Wait for confirmed volume expansion or support test.\n- Target Horizon: Review quarterly."

    if not ai_client: return deterministic_verdict

    prompt = f"""
    You are an institutional Indian equity portfolio committee. Evaluate NSE Stock: {sym}
    Quantitative Fundamentals: Market Cap: INR {stock_data['Market Cap (Cr)']} Cr | P/E: {stock_data['P/E']} | ROE: {stock_data['ROE (%)']}% | D/E: {stock_data['Debt/Equity']}
    Technicals & Price Action: Current Price: INR {stock_data['Price']} | 52W High: INR {stock_data['52W High']} | RSI (14): {stock_data['RSI(14)']} | Volume Surge: {stock_data['Vol Ratio']}
    Classified Setup: {pattern}

    Format your response EXACTLY into these lines:
    Verdict: **[BUY]**, **[SELL]**, **[WATCH]**, or **[AVOID]**
    Setup Quality: [1 sentence on the Breakout/Pullback/Momentum setup alignment]
    Holding Horizon: [Optimal holding period, e.g. 6-12 months, 1-3 years]
    """

    for model_name in ["gemini-2.5-flash", "gemini-1.5-flash"]:
        try:
            res = ai_client.models.generate_content(model=model_name, contents=prompt)
            if res and res.text: return res.text.strip()
        except Exception: continue

    return deterministic_verdict


# =========================================================
# 5. TAB 5: SUPERSTAR SMART MONEY ENGINE
# =========================================================
@st.cache_data(ttl=3600)
def get_superstar_portfolio(investor_name):
    portfolios = {
        "Radhakishan Damani": [
            {"Stock": "DMART (Avenue Supermarts)", "Sector": "Retail", "Change (QoQ)": "Unchanged"},
            {"Stock": "VST Industries", "Sector": "Tobacco", "Change (QoQ)": "Unchanged"},
            {"Stock": "India Cements", "Sector": "Cement", "Change (QoQ)": "Unchanged"}
        ],
        "Rekha Jhunjhunwala (Rare Enterprises)": [
            {"Stock": "Titan Company", "Sector": "Consumer Durables", "Change (QoQ)": "Unchanged"},
            {"Stock": "Fortis Healthcare", "Sector": "Healthcare", "Change (QoQ)": "Unchanged"},
            {"Stock": "Agro Tech Foods", "Sector": "FMCG", "Change (QoQ)": "+0.5% (Added)"}
        ],
        "Sunil Singhania (Abakkus)": [
            {"Stock": "Arvind Fashions", "Sector": "Retail", "Change (QoQ)": "Aggressive Accumulation (+0.8%)"},
            {"Stock": "Afcom Holdings", "Sector": "Logistics", "Change (QoQ)": "Fresh Entry (+1.97%)"},
            {"Stock": "TTK Healthcare", "Sector": "Healthcare", "Change (QoQ)": "Fresh Entry (+2.07%)"}
        ],
        "Akash Bhanshali": [
            {"Stock": "Gujarat Fluorochemicals", "Sector": "Chemicals", "Change (QoQ)": "Unchanged"},
            {"Stock": "Laurus Labs", "Sector": "Pharmaceuticals", "Change (QoQ)": "Unchanged"},
            {"Stock": "One97 Communications (Paytm)", "Sector": "Fintech", "Change (QoQ)": "-0.01% (Trimmed)"}
        ],
        "Ashish Kacholia": [
            {"Stock": "Shaily Engineering Plastics", "Sector": "Plastics", "Change (QoQ)": "Unchanged"},
            {"Stock": "Knowledge Marine & Eng", "Sector": "Shipping", "Change (QoQ)": "Unchanged"},
            {"Stock": "TechEra Engineering", "Sector": "Capital Goods", "Change (QoQ)": "Fresh Entry"}
        ],
        "Mukul Agrawal": [
            {"Stock": "ESDS Software", "Sector": "IT Software", "Change (QoQ)": "Fresh Entry"},
            {"Stock": "ASM Technologies", "Sector": "IT Services", "Change (QoQ)": "+1.2% (Added)"},
            {"Stock": "Raymond", "Sector": "Textiles", "Change (QoQ)": "Unchanged"}
        ],
        "Premji and Associates": [
            {"Stock": "Wipro", "Sector": "IT Services", "Change (QoQ)": "Unchanged"}
        ],
        "Nemish S Shah": [
            {"Stock": "Carborundum Universal", "Sector": "Industrial Products", "Change (QoQ)": "Block Deal Buy"},
            {"Stock": "Popular Foundations", "Sector": "Construction", "Change (QoQ)": "Block Deal Buy"}
        ],
        "Vijay Kedia": [
            {"Stock": "Om Infra", "Sector": "Infrastructure", "Change (QoQ)": "Unchanged (2.49% Stake)"},
            {"Stock": "Vaibhav Global", "Sector": "Retail", "Change (QoQ)": "Unchanged (2.05% Stake)"},
            {"Stock": "Patel Engineering", "Sector": "Construction", "Change (QoQ)": "Unchanged (1.01% Stake)"}
        ],
        "Ashish Dhawan": [
            {"Stock": "M&M Financial Services", "Sector": "NBFC", "Change (QoQ)": "Unchanged"},
            {"Stock": "Religare Enterprises", "Sector": "NBFC", "Change (QoQ)": "Unchanged"},
            {"Stock": "IIFL Finance", "Sector": "NBFC", "Change (QoQ)": "Unchanged"}
        ]
    }
    return pd.DataFrame(portfolios.get(investor_name, [{"Stock": "N/A", "Sector": "N/A", "Change (QoQ)": "N/A"}]))

@st.cache_data(ttl=3600)
def generate_superstar_notes(investor, new_buys):
    if not new_buys: return "No fresh entries or additions detected this quarter."
    default_rationale = f"Smart money accumulation detected by {investor} in {', '.join(new_buys)}. Institutional positioning often precedes margin expansion or order book execution."
    if not ai_client: return default_rationale
    
    prompt = f"Investor {investor} bought {', '.join(new_buys)}. Write a professional 2-sentence rationale outlining potential catalysts."
    for model_name in ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.5-flash-lite"]:
        try:
            res = ai_client.models.generate_content(model=model_name, contents=prompt)
            if res.text: return res.text.strip()
        except: continue
    return default_rationale


# =========================================================
# 6. UI WORKFLOW & TAB RENDERING
# =========================================================
LARGE_MID_CAP = {"Defense & Capital Goods": ["HAL.NS", "BEL.NS", "BDL.NS", "MAZDOCK.NS"], "EMS": ["DIXON.NS", "KAYNES.NS"]}
SMALLCAP = {"High-Growth Small-Caps": ["MARKSANS.NS", "GENUSPOWER.NS", "SAKSOFT.NS", "PCBL.NS"]}
PENNY = {"High-Volume Penny": ["SUZLON.NS", "RPOWER.NS", "JPPOWER.NS", "YESBANK.NS"]}

tab_core, tab_smallcap, tab_penny, tab_multibagger, tab_smart_money = st.tabs([
    "🏛️ Large & Mid-Cap Core", "🚀 Small-Caps", "⚠️ Penny & Micro-Caps", "🏆 AI Multibagger Stocks", "🐋 Superstar Smart Money"
])

def render_pipeline_ui(theme_dict, strategy, title):
    st.subheader(title)
    if st.button(f"🚀 Run Fast Pipeline", key=f"btn_{strategy}"):
        with st.spinner("Native Quant & TradingView Scanning..."):
            tasks = [(t, t_name, strategy) for t_name, tickers in theme_dict.items() for t in tickers]
            all_cands = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(analyze_stock, t[0], t[1], t[2]) for t in tasks]
                for future in concurrent.futures.as_completed(futures):
                    if future.result(): all_cands.append(future.result())

            df = pd.DataFrame(all_cands)
            if not df.empty:
                df = df.sort_values(by=["Overall Score (/100)"], ascending=False).reset_index(drop=True)
                st.dataframe(df[["Symbol", "Price (₹)", "Market Cap (Cr)", "TV RSI(14)", "ROE (%)", "Debt/Equity", "Overall Score (/100)", "Tier"]], use_container_width=True)

with tab_core: render_pipeline_ui(LARGE_MID_CAP, "core", "Secular Growth & Market Leaders")
with tab_smallcap: render_pipeline_ui(SMALLCAP, "smallcap", "Micro/Small-Cap Compounders")
with tab_penny: render_pipeline_ui(PENNY, "penny", "High-Risk Penny & Nano-Caps")

with tab_multibagger:
    st.subheader("🏆 Technical & Fundamental Multibagger Screener")
    st.caption("Screens for Breakouts, Support Pullbacks, and Trend Momentum combined with Multibagger Fundamentals.")

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
                    if res: scanned_records.append(res)

        if not scanned_records:
            st.error("Market data feed temporarily unavailable.")
        else:
            df_screen = pd.DataFrame(scanned_records)
            if pattern_filter != "All Setups":
                df_screen = df_screen[df_screen["Setup Pattern"] == pattern_filter]

            if df_screen.empty:
                st.warning(f"No stocks currently qualify for {pattern_filter}. Showing all setups instead.")
                df_screen = pd.DataFrame(scanned_records)

            df_screen = df_screen.sort_values(by=["RSI(14)", "ROE (%)"], ascending=[False, False]).reset_index(drop=True)
            st.dataframe(df_screen[["Symbol", "Price", "Setup Pattern", "RSI(14)", "Vol Ratio", "ROE (%)", "Debt/Equity", "P/E", "Multibagger Base"]], use_container_width=True)

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
                    c3.metric("ROE / D/E", f"{cand['ROE (%)']}% / {cand['Debt/Equity']}")
                    c4.metric("Volume Surge", cand["Vol Ratio"])
                    st.markdown(verdict_map.get(sym, "Verdict generating..."))


with tab_smart_money:
    st.subheader("🐋 Whale Tracker: Top 10 Superstar Investors' Holdings")
    
    investors = [
        "Radhakishan Damani", "Rekha Jhunjhunwala (Rare Enterprises)", "Sunil Singhania (Abakkus)",
        "Akash Bhanshali", "Ashish Kacholia", "Mukul Agrawal", "Premji and Associates",
        "Nemish S Shah", "Vijay Kedia", "Ashish Dhawan"
    ]
    
    investor_choice = st.selectbox("Select Superstar Investor:", investors)
    
    if st.button(f"Load {investor_choice} Portfolio"):
        portfolio_df = get_superstar_portfolio(investor_choice)
        
        def highlight_fresh_buys(row):
            if 'Fresh Entry' in str(row['Change (QoQ)']) or '+' in str(row['Change (QoQ)']) or 'Block Deal Buy' in str(row['Change (QoQ)']):
                return ['background-color: rgba(0, 255, 0, 0.15)'] * len(row)
            return [''] * len(row)
            
        st.dataframe(portfolio_df.style.apply(highlight_fresh_buys, axis=1), use_container_width=True)
        
        new_buys_df = portfolio_df[portfolio_df['Change (QoQ)'].str.contains('Fresh Entry|\+|Block Deal Buy', case=False, na=False, regex=True)]
        if not new_buys_df.empty:
            st.markdown("### 🤖 AI Smart Money Notes on New Buys")
            with st.spinner("AI analyzing acquisitions..."):
                st.info(generate_superstar_notes(investor_choice, new_buys_df['Stock'].tolist()))
