import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import xgboost as xgb
from datetime import datetime
import plotly.graph_objects as go
import warnings

warnings.filterwarnings('ignore')

st.set_page_config(page_title="Arpitha's Stock Predictor", layout="wide")
st.title("🚀 Arpitha's 2-3 Week Stock Predictor")
st.markdown("**Horizon:** 10-15 Trading Days | **Capital:** ₹40,000")

# ================== SIDEBAR ==================
st.sidebar.header("⚙️ Settings")
capital = st.sidebar.number_input("Total Capital (₹)", value=40000, min_value=10000, step=5000)
max_stocks = st.sidebar.slider("Max Stocks", 3, 6, 5)
risk_level = st.sidebar.selectbox("Risk Level", ["Moderate", "Aggressive"])

stop_loss_pct = 8 if risk_level == "Moderate" else 10

# ================== TICKERS ==================
tickers = [
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS",
    "TCS.NS", "INFY.NS", "LT.NS", "AXISBANK.NS", "SUNPHARMA.NS",
    "BEL.NS", "HAL.NS", "TRENT.NS", "POLYCAB.NS"
]

# ================== FUNCTIONS ==================
@st.cache_data(ttl=3600)
def get_data(ticker):
    try:
        return yf.download(ticker, period="2y", progress=False)
    except:
        return pd.DataFrame()

def add_features(df, nifty):
    if df.empty:
        return pd.DataFrame()
    df = df.copy()
    df['Returns'] = df['Close'].pct_change()
    
    for p in [5, 10, 20, 50]:
        df[f'SMA_{p}'] = df['Close'].rolling(p).mean()
        df[f'EMA_{p}'] = df['Close'].ewm(span=p).mean()
    
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['MACD'] = df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()
    df['Momentum_10'] = df['Close'] / df['Close'].shift(10) - 1
    df['Vol_10'] = df['Returns'].rolling(10).std()
    df['Volume_Ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()
    df['Rel_Nifty'] = (df['Close'] / nifty['Close'].reindex(df.index).ffill()) - 1
    
    df['Target'] = df['Close'].shift(-12) / df['Close'] - 1
    return df.dropna()

def train_and_predict(ticker, nifty):
    try:
        df = get_data(ticker)
        if len(df) < 400:
            return None
        
        df_feat = add_features(df, nifty)
        if df_feat.empty:
            return None
            
        feature_cols = [col for col in df_feat.columns if col not in 
                       ['Target', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']]
        
        X = df_feat[feature_cols]
        y = df_feat['Target']
        
        model = xgb.XGBRegressor(
            n_estimators=300, 
            learning_rate=0.05, 
            max_depth=6,
            subsample=0.8, 
            colsample_bytree=0.8, 
            random_state=42
        )
        model.fit(X, y)
        
        latest = df_feat.iloc[-1:]
        pred_return = model.predict(latest[feature_cols])[0]
        current_price = round(df['Close'].iloc[-1], 2)
        
        return {
            'Ticker': ticker.replace('.NS', ''),
            'Price': current_price,
            'Pred_Return': round(pred_return * 100, 2),
            'Signal': "STRONG BUY" if pred_return > 0.12 else "BUY" if pred_return > 0.08 else "HOLD",
            'Volume': int(df['Volume'].iloc[-1])
        }
    except Exception as e:
        st.warning(f"Error with {ticker}: {str(e)}")
        return None

# ================== MAIN ==================
if st.button("🔄 Run Fresh Prediction", type="primary"):
    with st.spinner("Analyzing 14 stocks for 2-3 week opportunities..."):
        nifty = get_data("^NSEI")
        results = []
        
        progress_bar = st.progress(0)
        for i, ticker in enumerate(tickers):
            res = train_and_predict(ticker, nifty)
            if res:
                results.append(res)
            progress_bar.progress((i + 1) / len(tickers))
        
        if results:
            df_pred = pd.DataFrame(results)
            df_pred = df_pred.sort_values('Pred_Return', ascending=False)
            st.session_state['predictions'] = df_pred
            st.success(f"✅ Analyzed {len(results)} stocks successfully!")
        else:
            st.error("❌ No data returned. Please try again later.")

# Display Results
if 'predictions' in st.session_state:
    df_pred = st.session_state['predictions']
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📊 Top Predictions")
        display_df = df_pred.head(10).copy()
        display_df['Suggested Allocation (₹)'] = (capital / max_stocks).round(0)
        st.dataframe(display_df, use_container_width=True)
    
    with col2:
        st.subheader("💰 Recommended Portfolio")
        buy_stocks = df_pred[df_pred['Signal'].str.contains("BUY")].head(max_stocks)
        
        if not buy_stocks.empty:
            for _, row in buy_stocks.iterrows():
                alloc = int(capital / len(buy_stocks))
                st.success(f"**{row['Ticker']}** → ₹{alloc} | +{row['Pred_Return']}%")
        else:
            st.warning("No strong BUY signals currently.")

    # Top 3 Charts
    st.subheader("📈 Top 3 Stock Charts")
    for _, stock in df_pred.head(3).iterrows():
