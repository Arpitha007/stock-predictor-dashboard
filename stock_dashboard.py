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
st.markdown("**Horizon:** 10-15 Trading Days | **Capital:** ₹40,000")

# ================== SIDEBAR ==================
st.sidebar.header("⚙️ Settings")
capital = st.sidebar.number_input("Total Capital (₹)", value=40000, min_value=10000, step=5000)
max_stocks = st.sidebar.slider("Max Stocks", 3, 6, 5)
risk_level = st.sidebar.selectbox("Risk Level", ["Moderate", "Aggressive"])

# ================== TICKERS (Reduced for stability) ==================
tickers = [
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", 
    "BHARTIARTL.NS", "TCS.NS", "INFY.NS", "LT.NS"
]

# ================== FUNCTIONS ==================
@st.cache_data(ttl=7200)  # Cache for 2 hours
def get_data(ticker):
    for attempt in range(3):  # Retry 3 times
        try:
            data = yf.download(ticker, period="2y", progress=False, timeout=10)
            if not data.empty:
                return data
            time.sleep(1)
        except:
            time.sleep(2)
    return pd.DataFrame()

def add_features(df, nifty):
    if df.empty or nifty.empty:
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
        
        model = xgb.XGBRegressor(n_estimators=250, learning_rate=0.06, max_depth=5,
                               subsample=0.8, colsample_bytree=0.8, random_state=42)
        model.fit(X, y)
        
        latest = df_feat.iloc[-1:]
        pred_return = model.predict(latest[feature_cols])[0]
        current_price = round(df['Close'].iloc[-1], 2)
        
        return {
            'Ticker': ticker.replace('.NS', ''),
            'Price': current_price,
            'Pred_Return': round(pred_return * 100, 2),
            'Signal': "STRONG BUY" if pred_return > 0.12 else "BUY" if pred_return > 0.08 else "HOLD"
        }
    except:
        return None

# ================== MAIN ==================
if st.button("🔄 Run Fresh Prediction", type="primary"):
    with st.spinner("Trying to fetch market data..."):
        nifty = get_data("^NSEI")
        results = []
        
        progress_bar = st.progress(0)
        for i, ticker in enumerate(tickers):
            res = train_and_predict(ticker, nifty)
            if res:
                results.append(res)
            progress_bar.progress((i + 1) / len(tickers))
            time.sleep(0.5)  # Small delay to avoid rate limit
        
        if results:
            df_pred = pd.DataFrame(results)
            df_pred = df_pred.sort_values('Pred_Return', ascending=False)
            st.session_state['predictions'] = df_pred
            st.success(f"✅ Successfully analyzed {len(results)} stocks!")
        else:
            st.error("❌ Still unable to fetch data from Yahoo Finance. This is a common temporary issue.")

# Display logic (same as before)
if 'predictions' in st.session_state:
    df_pred = st.session_state['predictions']
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📊 Top Predictions")
        display_df = df_pred.head(8).copy()
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
            st.warning("No strong BUY signals right now.")

    st.subheader("📈 Top 2 Stock Charts")
    for _, stock in df_pred.head(2).iterrows():
        ticker_full = stock['Ticker'] + ".NS"
        data = get_data(ticker_full).tail(60)
        if not data.empty:
            fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'],
                                                low=data['Low'], close=data['Close'])])
            fig.update_layout(title=f"{stock['Ticker']} | Pred: +{stock['Pred_Return']}%", height=380)
            st.plotly_chart(fig, use_container_width=True)

else:
    st.info("👆 Click **Run Fresh Prediction**")

st.caption("⚠️ yfinance can be unstable on cloud. Try multiple times or run locally.")
