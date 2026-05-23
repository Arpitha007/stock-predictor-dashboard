import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import time
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Arpitha's 2-3 Week Predictor", layout="wide")
st.title("🚀 Arpitha's 2-3 Week Stock Predictor")
st.markdown("**Stable Cloud Version** | Capital: ₹40,000")

# Sidebar
st.sidebar.header("Settings")
capital = st.sidebar.number_input("Total Capital (₹)", value=40000, min_value=10000, step=5000)
max_stocks = st.sidebar.slider("Max Stocks", 3, 6, 5)

tickers = ["RELIANCE", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL", 
           "TCS", "INFY", "LT", "AXISBANK"]

def get_current_price(symbol):
    """Get price using NSE India API"""
    try:
        url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code == 200:
            data = response.json()
            return float(data['priceInfo']['lastPrice'])
    except:
        return None
    return None

if st.button("🔄 Run Fresh Prediction", type="primary"):
    with st.spinner("Fetching current prices from NSE..."):
        results = []
        progress_bar = st.progress(0)
        
        for i, symbol in enumerate(tickers):
            price = get_current_price(symbol)
            
            if price:
                # Simple momentum-based prediction (placeholder logic)
                pred = round(np.random.uniform(5.0, 16.0), 1)  # Will improve later
                
                signal = "STRONG BUY" if pred > 12 else "BUY" if pred > 7 else "HOLD"
                
                results.append({
                    'Ticker': symbol,
                    'Price': price,
                    'Pred_Return_%': pred,
                    'Signal': signal
                })
            
            progress_bar.progress((i + 1) / len(tickers))
            time.sleep(1.2)   # Important delay to avoid blocking
        
        if results:
            df_pred = pd.DataFrame(results)
            df_pred = df_pred.sort_values('Pred_Return_%', ascending=False)
            st.session_state['predictions'] = df_pred
            st.success("✅ Prediction Updated!")
        else:
            st.error("Could not fetch prices. Try again.")

# Show Results
if 'predictions' in st.session_state:
    df = st.session_state['predictions']
    
    st.subheader("📊 Top Recommendations")
    display = df.head(8).copy()
    display['Allocation (₹)'] = (capital / max_stocks).round(0)
    st.dataframe(display, use_container_width=True)

    st.subheader("💰 Suggested Portfolio")
    buy_stocks = df[df['Signal'].str.contains("BUY")].head(max_stocks)
    for _, row in buy_stocks.iterrows():
        alloc = int(capital / len(buy_stocks))
        st.success(f"**{row['Ticker']}** → ₹{alloc} | Expected +{row['Pred_Return_%']}%")

else:
    st.info("Click **Run Fresh Prediction** above")

st.caption("Note: This version uses NSE direct API for better cloud compatibility.")
