import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import xgboost as xgb
import plotly.graph_objects as go
import warnings
import time

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Arpitha's Stock Predictor", layout="wide")
st.title("🚀 Arpitha's 2-3 Week Stock Predictor")
st.markdown("**Running Locally** | Horizon: 10-15 Trading Days | Capital: ₹40,000")

# Sidebar
st.sidebar.header("Settings")
capital = st.sidebar.number_input("Total Capital (₹)", value=40000, min_value=10000)
max_stocks = st.sidebar.slider("Max Stocks", 3, 6, 5)
risk_level = st.sidebar.selectbox("Risk Level", ["Moderate", "Aggressive"])

# Tickers - Reduced for speed
tickers = ["RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", 
           "BHARTIARTL.NS", "TCS.NS", "INFY.NS", "LT.NS", "AXISBANK.NS"]

@st.cache_data(ttl=3600)
def get_data(ticker):
    for attempt in range(4):
        try:
            df = yf.download(ticker, period="2y", progress=False, timeout=15)
            if not df.empty and len(df) > 300:
                return df
            time.sleep(1.5)
        except:
            time.sleep(2)
    return pd.DataFrame()

def add_features(df, nifty):
    if df.empty or nifty.empty:
        return pd.DataFrame()
    df = df.copy()
    
    df['Returns'] = df['Close'].pct_change()
    for p in [5,10,20]:
        df[f'SMA_{p}'] = df['Close'].rolling(p).mean()
        df[f'EMA_{p}'] = df['Close'].ewm(span=p).mean()
    
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['Momentum_10'] = df['Close'] / df['Close'].shift(10) - 1
    df['Target'] = df['Close'].shift(-12) / df['Close'] - 1
    
    return df.dropna()

# Main Button
if st.button("🔄 Run Fresh Prediction", type="primary"):
    with st.spinner("Fetching data from Yahoo Finance..."):
        nifty = get_data("^NSEI")
        results = []
        
        for i, ticker in enumerate(tickers):
            st.write(f"Analyzing {ticker.replace('.NS','')}...")
            df = get_data(ticker)
            if len(df) < 400:
                continue
                
            df_feat = add_features(df, nifty)
            if df_feat.empty:
                continue
                
            feature_cols = [col for col in df_feat.columns if col not in 
                           ['Target', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']]
            
            X = df_feat[feature_cols]
            y = df_feat['Target']
            
            model = xgb.XGBRegressor(n_estimators=200, learning_rate=0.07, max_depth=5, random_state=42)
            model.fit(X, y)
            
            latest = df_feat.iloc[-1:]
            pred_return = model.predict(latest[feature_cols])[0]
            
            results.append({
                'Ticker': ticker.replace('.NS', ''),
                'Price': round(df['Close'].iloc[-1], 2),
                'Pred_Return': round(pred_return * 100, 2),
                'Signal': "STRONG BUY" if pred_return > 0.12 else "BUY" if pred_return > 0.08 else "HOLD"
            })
        
        if results:
            df_pred = pd.DataFrame(results).sort_values('Pred_Return', ascending=False)
            st.session_state['predictions'] = df_pred
            st.success("✅ Prediction Complete!")
        else:
            st.error("Could not fetch data. Try again in 2-3 minutes.")

# Display
if 'predictions' in st.session_state:
    df_pred = st.session_state['predictions']
    st.subheader("Top Predictions")
    display_df = df_pred.head(8).copy()
    display_df['Allocation (₹)'] = (capital / max_stocks).round(0)
    st.dataframe(display_df, use_container_width=True)

st.info("💡 **Tip:** Local version works much better than Streamlit Cloud.")
