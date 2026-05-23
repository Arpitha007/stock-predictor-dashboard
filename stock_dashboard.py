import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import xgboost as xgb
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Arpitha's 2-3 Week Stock Predictor", layout="wide")
st.title("🚀 Arpitha's 2-3 Week Stock Momentum Predictor")
st.markdown("**Horizon:** 10-15 Trading Days | **Capital:** ₹40,000 | **Risk:** Moderate-Aggressive")

# ================== SIDEBAR ==================
st.sidebar.header("⚙️ Settings")

capital = st.sidebar.number_input("Total Capital (₹)", value=40000, min_value=10000, step=5000)
max_stocks = st.sidebar.slider("Max Stocks in Portfolio", 3, 6, 5)
risk_level = st.sidebar.selectbox("Risk Level", ["Moderate", "Aggressive"])

stop_loss_pct = 8 if risk_level == "Moderate" else 10
target_pct = 15 if risk_level == "Moderate" else 20

st.sidebar.info(f"Recommended Stop Loss: **-{stop_loss_pct}%** | Target: **+{target_pct}%**")

# ================== TICKERS ==================
tickers = [
    "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "BHARTIARTL.NS",
    "TCS.NS", "INFY.NS", "LT.NS", "AXISBANK.NS", "SUNPHARMA.NS",
    "BEL.NS", "HAL.NS", "TRENT.NS", "POLYCAB.NS", "RENEW.NS"
]

# ================== FUNCTIONS ==================
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_data(ticker):
    return yf.download(ticker, period="2y", progress=False)

def add_features(df, nifty):
    df = df.copy()
    df['Returns'] = df['Close'].pct_change()
    
    for p in [5,10,20,50]:
        df[f'SMA_{p}'] = df['Close'].rolling(p).mean()
        df[f'EMA_{p}'] = df['Close'].ewm(span=p).mean()
    
    df['RSI'] = 100 - (100 / (1 + (df['Close'].diff().where(lambda x: x>0,0).rolling(14).mean() /
                                 -df['Close'].diff().where(lambda x: x<0,0).rolling(14).mean())))
    
    df['MACD'] = df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()
    df['Momentum_10'] = df['Close']/df['Close'].shift(10) - 1
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
        feature_cols = [col for col in df_feat.columns if col not in 
                       ['Target','Open','High','Low','Close','Adj Close','Volume']]
        
        X = df_feat[feature_cols]
        y = df_feat['Target']
        
        model = xgb.XGBRegressor(n_estimators=400, learning_rate=0.04, max_depth=6,
                               subsample=0.85, colsample_bytree=0.8, random_state=42)
        model.fit(X, y)
        
        latest = df_feat.iloc[-1:]
        pred_return = model.predict(latest[feature_cols])[0]
        current_price = df['Close'].iloc[-1]
        
        return {
            'Ticker': ticker.replace('.NS', ''),
            'Price': round(current_price, 2),
            'Pred_Return': round(pred_return * 100, 2),
            'Signal': "STRONG BUY" if pred_return > 0.12 else "BUY" if pred_return > 0.08 else "HOLD",
            'Volume': int(df['Volume'].iloc[-1])
        }
    except:
        return None

# ================== MAIN DASHBOARD ==================
if st.button("🔄 Run Fresh Prediction"):
    with st.spinner("Analyzing market for best 2-3 week opportunities..."):
        nifty = get_data("^NSEI")
        results = []
        
        for ticker in tickers:
            res = train_and_predict(ticker, nifty)
            if res:
                results.append(res)
        
        df_pred = pd.DataFrame(results)
        df_pred = df_pred.sort_values('Pred_Return', ascending=False)
        
        # Save to session state
        st.session_state['predictions'] = df_pred

# Display Results
if 'predictions' in st.session_state:
    df_pred = st.session_state['predictions']
    
    col1, col2 = st.columns([2,1])
    
    with col1:
        st.subheader("📊 Top Predictions")
        display_df = df_pred.head(10).copy()
        display_df['Allocation (₹)'] = (capital / max_stocks).round(0)
        st.dataframe(display_df, use_container_width=True)
    
    with col2:
        st.subheader("Portfolio Suggestion")
        top_stocks = df_pred[df_pred['Signal'].str.contains("BUY")].head(max_stocks)
        
        if not top_stocks.empty:
            st.write("**Recommended Portfolio:**")
            for _, row in top_stocks.iterrows():
                alloc = int(capital / len(top_stocks))
                st.success(f"{row['Ticker']} → ₹{alloc} | Expected: **+{row['Pred_Return']}%**")
        
            total_expected = (top_stocks['Pred_Return'].mean() * capital / 100).round(0)
            st.metric("Expected Portfolio Gain", f"₹{total_expected}", f"{top_stocks['Pred_Return'].mean():.1f}%")

    # Charts for Top 3
    st.subheader("📈 Top 3 Stock Charts (Last 3 Months)")
    top3 = df_pred.head(3)
    
    for _, stock in top3.iterrows():
        ticker = stock['Ticker'] + ".NS"
        data = get_data(ticker).tail(63)  # ~3 months
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=data.index,
                    open=data['Open'], high=data['High'],
                    low=data['Low'], close=data['Close'], name="Price"))
        fig.update_layout(title=f"{stock['Ticker']} - Current: ₹{stock['Price']} | Pred: +{stock['Pred_Return']}%",
                         height=400)
        st.plotly_chart(fig, use_container_width=True)

    # Portfolio Tracker
    st.subheader("📝 Your Portfolio Tracker")
    if 'portfolio' not in st.session_state:
        st.session_state['portfolio'] = pd.DataFrame(columns=['Ticker', 'Buy_Price', 'Qty', 'Stop_Loss'])
    
    with st.form("add_trade"):
        ticker_input = st.selectbox("Add Stock", df_pred['Ticker'].tolist())
        buy_price = st.number_input("Buy Price", value=100.0)
        qty = st.number_input("Quantity", value=10, min_value=1)
        submitted = st.form_submit_button("Add to Portfolio")
        
        if submitted:
            new_row = pd.DataFrame([{
                'Ticker': ticker_input,
                'Buy_Price': buy_price,
                'Qty': qty,
                'Stop_Loss': round(buy_price * (1 - stop_loss_pct/100), 2)
            }])
            st.session_state['portfolio'] = pd.concat([st.session_state['portfolio'], new_row], ignore_index=True)
    
    if not st.session_state['portfolio'].empty:
        st.dataframe(st.session_state['portfolio'])

else:
    st.info("Click **Run Fresh Prediction** to get latest recommendations")

st.caption("Model built for educational & personal use only. Past performance ≠ future results. Always do your own research.")
