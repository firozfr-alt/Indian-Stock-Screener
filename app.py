# Fetch data first so price can be embedded into the expander title
market_data = fetch_market_sentiment()

if market_data.get("price", 0.0) > 0:
    prefix = "Nifty BeES: " if market_data.get("is_etf") else "Nifty 50: "
    # NEW: Formats the header bar to show points and percentage
    header_title = f"📊 Current Indian Market Sentiment ({prefix}₹{market_data['price']:,.2f} | {market_data['daily_pts']:+,.2f} pts / {market_data['daily_pct']:+.2f}%)"
else:
    header_title = "📊 Current Indian Market Sentiment (Nifty 50)"

with st.expander(header_title, expanded=True):
    if market_data.get("price", 0.0) > 0:
        m1, m2, m3, m4 = st.columns(4)
        price_label = "Nifty 50 (Proxy ETF)" if market_data.get("is_etf") else "Nifty 50 Current Price"
        
        # NEW: Combine points and percentage into a single delta string for Streamlit
        delta_str = f"{market_data['daily_pts']:+,.2f} ({market_data['daily_pct']:+.2f}%)"
        
        m1.metric(price_label, f"₹{market_data['price']:,.2f}", delta=delta_str)
        m2.metric("1-Month Momentum", f"{market_data['ret_1m']:+.2f}%")
        m3.metric("6-Month Momentum", f"{market_data['ret_6m']:+.2f}%")
        m4.metric("Quant Trend", market_data['trend'])
        st.divider()
        
    st.markdown(market_data.get("sentiment", ""))
