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
st.markdown("**Stable Technical Momentum Model** | Capital: ₹40,000")

# ================== SIDEBAR ==================
st.sidebar.header("⚙️ Settings")
capital = st.sidebar.number_input("Total Capital (₹)", value=40000, min_value=10000, step=5000)
max_stocks = st.sidebar.slider("Max Stocks in Portfolio", 3, 6, 5)

# ================== TICKERS ==================
tickers = ["RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", 
           "BHARTIARTL.NS", "TCS.NS", "INFY.NS", "LT.NS", "AXISBANK.NS"]

# ================== FUNCTIONS ==================
@st.cache_data(ttl=7200)
def get_data(ticker):
    """Download data with multiple retries"""
    for attempt in range(5):
        try:
            df = yf.download(ticker, period="2y", progress=False, timeout=15)
            if not df.empty and len(df) > 250:
                return df
            time.sleep(1.5)
        except:
            time.sleep(2)
    return pd.DataFrame()

if st.button("🔄 Run Fresh Prediction", type="primary"):
    with st.spinner("Fetching market data... This may take 30-60 seconds"):
        results = []
        nifty = get_data("^NSEI")
        
        progress_bar = st.progress(0)
        
        for i, ticker in enumerate(tickers):
            df = get_data(ticker)
            if len(df) < 300:
                progress_bar.progress((i + 1) / len(tickers))
                continue
            
            try:
                # Safe calculations
                close = float(df['Close'].iloc[-1])
                close_10 = float(df['Close'].iloc[-11]) if len(df) > 11 else close
                mom_10 = (close / close_10 - 1) * 100
                
                # RSI with safety
                delta = df['Close'].diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean().iloc[-1]
                loss = -delta.where(delta < 0, 0).rolling(14).mean().iloc[-1]
                
                if loss == 0:
                    rsi = 100.0
                else:
                    rsi = 100 - (100 / (1 + gain / loss))
                
                # Projected Return (conservative)
                pred_return = round(mom_10 * 1.5, 2)
                
                signal = "STRONG BUY" if pred_return > 12 else "BUY" if pred_return > 6 else "HOLD"
                
                results.append({
                    'Ticker': ticker.replace('.NS', ''),
                    'Price': round(close, 2),
                    'Pred_Return_%': pred_return,
                    'Signal': signal,
                    'RSI': round(float(rsi), 1)
                })
            except:
                pass  # Skip problematic stock silently
            
            progress_bar.progress((i + 1) / len(tickers))
            time.sleep(0.7)
        
        if results:
            df_pred = pd.DataFrame(results)
            df_pred = df_pred.sort_values('Pred_Return_%', ascending=False)
            st.session_state['predictions'] = df_pred
            st.success(f"✅ Analyzed {len(results)} stocks successfully!")
        else:
            st.error("❌ Could not fetch sufficient data. Please try again in 5 minutes.")

# ================== DISPLAY ==================
if 'predictions' in st.session_state:
    df_pred = st.session_state['predictions']
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📊 Top Predictions")
        display_df = df_pred.head(8).copy()
        display_df['Allocation (₹)'] = (capital / max_stocks).round(0)
        st.dataframe(display_df, use_container_width=True)
    
    with col2:
        st.subheader("💰 Recommended Portfolio")
        buy_df = df_pred[df_pred['Signal'].str.contains("BUY")].head(max_stocks)
        if not buy_df.empty:
            for _, row in buy_df.iterrows():
                alloc = int(capital / len(buy_df))
                st.success(f"**{row['Ticker']}** → ₹{alloc} | **+{row['Pred_Return_%']}%**")
        else:
            st.warning("No strong BUY signals currently.")

    # Charts - Only if data available
    st.subheader("📈 Top 2 Stock Charts")
    for _, stock in df_pred.head(2).iterrows():
        data = get_data(stock['Ticker'] + ".NS").tail(60)
        if not data.empty:
            fig = go.Figure(data=[go.Candlestick(
                x=data.index,
                open=data['Open'],
                high=data['High'],
                low=data['Low'],
                close=data['Close']
            )])
            fig.update_layout(
                title=f"{stock['Ticker']} | Current: ₹{stock['Price']} | Pred: +{stock['Pred_Return_%']}%",
                height=380
            )
            st.plotly_chart(fig, use_container_width=True)

else:
    st.info("👆 Click **Run Fresh Prediction** to analyze stocks")

st.caption("⚠️ Educational tool only. Not financial advice. Always verify before investing.")
