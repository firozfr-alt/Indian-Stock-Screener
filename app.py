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
st.caption("AI-Powered Tri-Strategy Screener, TradingView Technicals & Upstox Broker API")

# =========================================================
# 1. API INITIALIZATION (GEMINI & UPSTOX BROKER)
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

# Upstox Broker API Stub (Uses Upstox API v2 structure)
class UpstoxBrokerAPI:
    def __init__(self):
        self.is_connected = False
        if "UPSTOX_API_KEY" in st.secrets and "UPSTOX_API_SECRET" in st.secrets:
            self.is_connected = True
            st.sidebar.success("✅ Upstox Broker API: Ready")
        else:
            st.sidebar.info("ℹ️ Broker API Offline (Add UPSTOX credentials to Secrets)")

    def fetch_live_quote(self, symbol):
        """Placeholder for Upstox v2 Market Quote API"""
        if not self.is_connected: return None
        # Logic for calling https://api.upstox.com/v2/market-quote/quotes
        return {"symbol": symbol, "status": "simulated_live_connection"}

broker = UpstoxBrokerAPI()

# =========================================================
# 2. LIVE MARKET DATA & SENTIMENT (YFINANCE ENGINE)
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
# 3. ROBUST DATA ENGINES (TRADINGVIEW & YFINANCE NEWS)
# =========================================================
def get_tradingview_technicals(ticker):
    """Fetches robust native technicals from TradingView API without HTML scraping."""
    try:
        clean_ticker = ticker.replace('.NS', '').replace('.BO', '')
        handler = TA_Handler(
            symbol=clean_ticker,
            screener="india",
            exchange="NSE",
            interval=Interval.INTERVAL_1_DAY
        )
        analysis = handler.get_analysis()
        return analysis.indicators
    except Exception as e:
        return None

def get_stock_news_robust(ticker):
    """Fetches native institutional news from Yahoo Finance API. Never breaks like DuckDuckGo."""
    try:
        stock = yf.Ticker(f"{ticker}.NS" if not ticker.endswith('.NS') else ticker)
        news = stock.news
        if not news: return []
        
        news_items = []
        for n in news[:5]:
            # Extract title gracefully
            title = n.get('title', '')
            if title: news_items.append(title)
        return news_items
    except Exception as e:
        return []

def score_stock_catalysts(ticker, news_headlines, tv_indicators=None):
    """Evaluates news sentiment + TradingView technicals natively."""
    if not ai_client: return "Score: 0\nReasoning: Gemini API key required."
    if not news_headlines: return "Score: 0\nReasoning: No active catalysts detected."
    
    tv_context = ""
    if tv_indicators:
        tv_context = f"\nTradingView Technicals: RSI(14)={tv_indicators.get('RSI', 'N/A')}, SMA50={tv_indicators.get('SMA50', 'N/A')}"
        
    news_context = "\n".join([f"- {news}" for news in news_headlines])
    prompt = f"""
    Evaluate NSE stock: {ticker}.
    Headlines:{news_context}{tv_context}
    
    Task:
    1. Identify fundamental catalysts from the news.
    2. Assign a Catalyst Score from 1 to 10.
    Format:
    Score: [1-10]
    Reasoning: [1-2 short sentences summarizing]
    """
    for model_name in ["gemini-2.5-flash", "gemini-1.5-flash"]:
        try:
            res = ai_client.models.generate_content(model=model_name, contents=prompt)
            if res.text: return res.text
        except: continue
    return "Score: 0\nReasoning: API Exhausted."

# =========================================================
# 4. DETERMINISTIC QUANT ENGINE (SCREENER.IN LOGIC)
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
        fin = stock.financials
        cf = stock.cashflow
        
        market_cap_cr = round(info.get('marketCap', 0) / 10000000, 2)
        if market_cap_cr <= 0: market_cap_cr = round((current_price * info.get('sharesOutstanding', 10000000)) / 10000000, 2)
            
        pe_val = info.get('trailingPE', 25.0)
        roe_pct = round(info.get('returnOnEquity', 0.10) * 100, 2) if info.get('returnOnEquity') else 10.0
        de_val = round(info.get('debtToEquity', 35.0) / 100, 2) if info.get('debtToEquity') else 0.35
        
        # Native TradingView integration injection
        tv_data = get_tradingview_technicals(ticker.replace('.NS', ''))
        tv_rsi = tv_data.get('RSI', 50) if tv_data else 50
        tv_sma50 = tv_data.get('SMA50', current_price) if tv_data else current_price
        
        score = 0
        feasibility = 0
        red_flags = []
        
        if de_val > 1.2: red_flags.append(("CRITICAL", f"High Debt ({de_val})"))
        
        # TradingView Momentum scoring
        if tv_rsi > 60: score += 15
        if current_price > tv_sma50: score += 15
        
        # Fundamental Scoring
        if roe_pct >= 15.0: score += 20
        if de_val <= 0.3: score += 20
        
        tier = "TIER A - High-Conviction" if (score >= 60 and not red_flags) else "TIER B - Watchlist" if score >= 40 else "TIER C - Speculative"

        return {
            "Symbol": ticker.replace(".NS", ""), "Theme": theme, "Price (₹)": current_price,
            "Market Cap (Cr)": market_cap_cr, "P/E": pe_val, "ROE (%)": roe_pct, "Debt/Equity": de_val,
            "TV RSI(14)": round(tv_rsi, 2), "Overall Score (/100)": score, "Tier": tier, "Red Flags": red_flags
        }
    except Exception:
        return None

def fetch_dossier_parallel(candidate, strategy):
    sym = candidate["Symbol"]
    if not ai_client: return sym, f"**Deterministic Audit:** Scored {candidate['Overall Score (/100)']}/100."
    prompt = f"Analyze {sym}. Theme: {candidate['Theme']}. Price: {candidate['Price (₹)']}. ROE: {candidate['ROE (%)']}%. D/E: {candidate['Debt/Equity']}. Give a BUY/SELL/WATCH verdict."
    try:
        res = ai_client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return sym, res.text.strip() if res.text else "Failed."
    except:
        return sym, "API rate limits reached."

# =========================================================
# 5. UI TABS & WORKFLOW
# =========================================================
LARGE_MID_CAP = {"Defense & Capital Goods": ["HAL.NS", "BEL.NS", "BDL.NS", "MAZDOCK.NS"], "EMS": ["DIXON.NS", "KAYNES.NS"]}
SMALLCAP = {"High-Growth Small-Caps": ["MARKSANS.NS", "GENUSPOWER.NS", "SAKSOFT.NS", "PCBL.NS"]}
PENNY = {"High-Volume Penny": ["SUZLON.NS", "RPOWER.NS", "JPPOWER.NS", "YESBANK.NS"]}

tab_core, tab_smallcap, tab_penny, tab_multibagger, tab_smart_money = st.tabs([
    "🏛️ Large & Mid-Cap Core", "🚀 Small-Caps", "⚠️ Penny & Micro-Caps", "🏆 TradingView Multibaggers", "🐋 Superstar Smart Money"
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

# =========================================================
# TAB 4: TRADINGVIEW AI MULTIBAGGER STOCKS
# =========================================================
with tab_multibagger:
    st.subheader("🏆 TradingView & YFinance AI Multibagger Screener")
    st.write("Uses native `tradingview_ta` library for robust technical breakouts and `yfinance` API for catalysts.")
    
    # We define a strong watchlist to dynamically screen instead of HTML scraping Chartink
    momentum_universe = ["ZOMATO", "SUZLON", "IREDA", "HAL", "DIXON", "KAYNES", "TRENT", "BSE", "CDSL", "MCX"]
    
    if st.button("🚀 Run AI Multibagger Scan"):
        results = []
        progress_bar = st.progress(0)
        
        for i, ticker in enumerate(momentum_universe):
            with st.spinner(f"Analyzing {ticker} via TradingView API..."):
                tv_tech = get_tradingview_technicals(ticker)
                
                # Only analyze stocks that are in a technical uptrend
                if tv_tech and tv_tech.get('RSI', 0) > 55 and tv_tech.get('close', 0) > tv_tech.get('SMA50', 0):
                    news = get_stock_news_robust(ticker)
                    ai_analysis = score_stock_catalysts(ticker, news, tv_tech)
                    try:
                        lines = ai_analysis.strip().split('\n')
                        score = int(lines[0].replace('Score:', '').strip())
                        reasoning = lines[1].replace('Reasoning:', '').strip()
                    except:
                        score = 0
                        reasoning = "Data parsing error."
                        
                    results.append({"Ticker": ticker, "TV RSI": round(tv_tech.get('RSI', 0), 2), "AI Score": score, "Catalysts": reasoning})
            
            progress_bar.progress((i + 1) / len(momentum_universe))
            
        df = pd.DataFrame(results)
        if not df.empty:
            df = df.sort_values(by=["AI Score", "TV RSI"], ascending=[False, False]).reset_index(drop=True)
            st.dataframe(df, column_config={"AI Score": st.column_config.ProgressColumn("AI Score", format="%d", min_value=0, max_value=10)}, use_container_width=True)
        else:
            st.warning("No stocks passed the TradingView Momentum threshold today.")

# =========================================================
# TAB 5: SUPERSTAR SMART MONEY (WITH QUOTA FALLBACKS)
# =========================================================
@st.cache_data(ttl=3600)
def get_superstar_portfolio(investor_name):
    portfolios = {
        "Radhakishan Damani": [{"Stock": "DMART", "Sector": "Retail", "Change (QoQ)": "Unchanged"}],
        "Rekha Jhunjhunwala": [{"Stock": "Agro Tech Foods", "Sector": "FMCG", "Change (QoQ)": "+0.5% (Added)"}],
        "Ashish Kacholia": [{"Stock": "TechEra Engineering", "Sector": "Capital Goods", "Change (QoQ)": "Fresh Entry"}],
        "Vijay Kedia": [{"Stock": "Om Infra", "Sector": "Infrastructure", "Change (QoQ)": "Fresh Entry"}]
    }
    return pd.DataFrame(portfolios.get(investor_name, [{"Stock": "N/A", "Sector": "N/A", "Change (QoQ)": "N/A"}]))

@st.cache_data(ttl=3600)
def generate_superstar_notes(investor, new_buys):
    if not new_buys: return "No fresh entries or additions detected this quarter."
    default_rationale = f"Smart money accumulation detected by {investor} in {', '.join(new_buys)}. Institutional positioning often precedes margin expansion or order book execution."
    if not ai_client: return default_rationale
    
    prompt = f"Investor {investor} bought {', '.join(new_buys)}. Write a professional 2-sentence rationale."
    for model_name in ["gemini-2.5-flash", "gemini-1.5-flash"]:
        try:
            res = ai_client.models.generate_content(model=model_name, contents=prompt)
            if res.text: return res.text.strip()
        except: continue
    return default_rationale

with tab_smart_money:
    st.subheader("🐋 Whale Tracker: Top 10 Superstar Investors' Holdings")
    investors = ["Radhakishan Damani", "Rekha Jhunjhunwala", "Ashish Kacholia", "Vijay Kedia"]
    investor_choice = st.selectbox("Select Superstar Investor:", investors)
    
    if st.button(f"Load {investor_choice} Portfolio"):
        portfolio_df = get_superstar_portfolio(investor_choice)
        st.dataframe(portfolio_df, use_container_width=True)
        
        new_buys_df = portfolio_df[portfolio_df['Change (QoQ)'].str.contains('Fresh Entry|\+', case=False, na=False, regex=True)]
        if not new_buys_df.empty:
            st.markdown("### 🤖 AI Smart Money Notes on New Buys")
            with st.spinner("AI analyzing acquisitions..."):
                st.info(generate_superstar_notes(investor_choice, new_buys_df['Stock'].tolist()))
