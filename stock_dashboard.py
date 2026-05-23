import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings
import time

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Arpitha's Stock Predictor", layout="wide")
st.title("🚀 Arpitha's 2-3 Week Stock Predictor")
st.markdown("**Simple Technical Momentum Model** | Capital: ₹40,000")

# Sidebar
st.sidebar.header("Settings")
capital = st.sidebar.number_input("Total Capital (₹)", value=40000)
max_stocks = st.sidebar.slider("Max Stocks", 3, 6, 5)

tickers = ["RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", 
           "BHARTIARTL.NS", "TCS.NS", "INFY.NS", "LT.NS", "AXISBANK.NS"]

@st.cache_data(ttl=3600)
def get_data(ticker):
    for _ in range(3):
        try:
            df = yf.download(ticker, period="2y", progress=False, timeout=10)
            if not df.empty:
                return df
            time.sleep(1)
        except:
            time.sleep(2)
    return pd.DataFrame()

if st.button("🔄 Run Fresh Prediction", type="primary"):
    with st.spinner("Fetching data..."):
        results = []
        nifty = get_data("^NSEI")
        
        for ticker in tickers:
            df = get_data(ticker)
            if len(df) < 300:
                continue
                
            # Simple Momentum Score
            df['Returns'] = df['Close'].pct_change()
            mom_10 = df['Close'].iloc[-1] / df['Close'].iloc[-11] - 1
            rsi = 100 - (100 / (1 + (df['Close'].diff().where(lambda x: x>0,0).rolling(14).mean() / 
                                    -df['Close'].diff().where(lambda x: x<0,0).rolling(14).mean())))
            vol = df['Returns'].rolling(20).std().iloc[-1]
            
            score = (mom_10 * 0.6) + ((rsi < 70).astype(int) * 0.3) - (vol * 2)
            
            pred_return = round(mom_10 * 100 * 1.8, 2)  # Rough projection
            
            results.append({
                'Ticker': ticker.replace('.NS', ''),
                'Price': round(df['Close'].iloc[-1], 2),
                'Pred_Return': pred_return,
                'Signal': "STRONG BUY" if pred_return > 12 else "BUY" if pred_return > 6 else "HOLD",
                'Momentum_Score': round(score, 3)
            })
        
        if results:
            df_pred = pd.DataFrame(results).sort_values('Pred_Return', ascending=False)
            st.session_state['predictions'] = df_pred
            st.success("✅ Done!")
        else:
            st.error("Data fetch failed. Try again.")

# Display
if 'predictions' in st.session_state:
    df_pred = st.session_state['predictions']
    st.subheader("Top Recommendations")
    disp = df_pred.head(8).copy()
    disp['Allocation (₹)'] = (capital / max_stocks).round(0)
    st.dataframe(disp, use_container_width=True)

st.caption("Simplified version - More stable on cloud")
