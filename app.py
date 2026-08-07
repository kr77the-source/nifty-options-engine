import time
from datetime import datetime, timedelta
import pytz
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="6 Core Strategies Live Engine", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    h1 { font-size: 20px !important; margin-bottom: 0px !important; }
    h2 { font-size: 16px !important; margin-top: 5px !important; }
    p, div, span, label { font-size: 13px !important; }
    hr { margin: 10px 0px !important; }
    .strat-tag { font-weight: bold; color: #00FF7F; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Pure Real Intraday Engine: 6 Core Strategies")
st.markdown("Strictly Real-Time Mathematical Scanner | Quantity: **10 Shares** | Zero Fake Data")

# NSE Stocks for Intraday (10 shares low risk)
STOCKS = {
    "Reliance": "RELIANCE.NS",
    "Tata Motors": "TATAMOTORS.NS",
    "SBI": "SBIN.NS",
    "Infosys": "INFY.NS"
}
TEST_QUANTITY = 10

def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

# Session States
if "active_live_trades" not in st.session_state:
    st.session_state.active_live_trades = {}

if "trade_history" not in st.session_state:
    st.session_state.trade_history = []

def calculate_6_strategies(df):
    """Calculates Real Technicals for 6 Core Strategies using pandas"""
    # 1. EMA Crossover
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    # 2. VWAP
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    
    # 3. MACD
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # 4. RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # 5. Bollinger Bands (20, 2)
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['STD_20'] = df['Close'].rolling(window=20).std()
    df['Upper_BB'] = df['SMA_20'] + (df['STD_20'] * 2)
    df['Lower_BB'] = df['SMA_20'] - (df['STD_20'] * 2)
    
    # 6. Volume Surge
    df['Vol_Avg_20'] = df['Volume'].rolling(window=20).mean()
    
    return df

def get_real_market_signal(symbol):
    try:
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        if df.empty or len(df) < 30:
            return "NONE", None, ""
            
        df = calculate_6_strategies(df)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        ltp = round(float(last['Close']), 2)
        
        # Strategy 1: EMA Crossover
        if last['EMA_9'] > last['EMA_21'] and prev['EMA_9'] <= prev['EMA_21']:
            return "LONG", ltp, "EMA Crossover"
            
        # Strategy 2: VWAP Bounce (Price crosses above VWAP)
        if last['Close'] > last['VWAP'] and prev['Close'] <= prev['VWAP']:
            return "LONG", ltp, "VWAP Bounce"
            
        # Strategy 3: MACD Crossover
        if last['MACD'] > last['Signal_Line'] and prev['MACD'] <= prev['Signal_Line']:
            return "LONG", ltp, "MACD Breakout"
            
        # Strategy 4: RSI Oversold Reversal
        if last['RSI'] > 30 and prev['RSI'] <= 30:
            return "LONG", ltp, "RSI Reversal"
            
        # Strategy 5: Bollinger Bands Breakout
        if last['Close'] > last['Upper_BB'] and prev['Close'] <= prev['Upper_BB']:
            return "LONG", ltp, "Bollinger Breakout"
            
        # Strategy 6: Volume Profile Surge
        if last['Volume'] > (last['Vol_Avg_20'] * 2.5) and last['Close'] > prev['Close']:
            return "LONG", ltp, "Volume Surge"

        return "NONE", ltp, ""
            
    except Exception as e:
        return "NONE", None, ""

@st.fragment(run_every=30)
def pure_live_scanner():
    now_ist = get_ist_time()
    current_time_str = now_ist.strftime('%H:%M:%S')
    st.info(f"🔄 **Engine Sync:** {current_time_str} IST | Scanning 6 Core Strategies on Real Market Data...")
    
    st.subheader("📡 Live Signals & Active Trades (10 Shares)")
    
    for stock_name, symbol in STOCKS.items():
        signal, live_price, strat_name = get_real_market_signal(symbol)
        
        # ENTRY LOGIC
        if live_price is not None and stock_name not in st.session_state.active_live_trades:
            if signal == "LONG":
                entry_price = live_price
                sl_price = round(entry_price - (entry_price * 0.005), 2)  
                target_price = round(entry_price + (entry_price * 0.01), 2) 
                
                st.session_state.active_live_trades[stock_name] = {
                    "Entry_Time": current_time_str,
                    "Stock": stock_name,
                    "Strategy": strat_name,
                    "Action": "LONG (BUY)",
                    "Qty": TEST_QUANTITY,
                    "Entry": entry_price,
                    "Current_LTP": live_price,
                    "SL": sl_price,
                    "Target": target_price,
                    "Status": "Running ⏳",
                    "Exit_Time": "--"
                }
                
        # RUNNING TRADE LOGIC (SL / Target tracking)
        elif stock_name in st.session_state.active_live_trades and live_price is not None:
            trade = st.session_state.active_live_trades[stock_name]
            trade["Current_LTP"] = live_price
            
            if live_price >= trade["Target"]:
                trade["Status"] = "Target Hit ✅"
                trade["Exit_Time"] = current_time_str
                trade["Exit_Price"] = live_price
                st.session_state.trade_history.append(trade)
                del st.session_state.active_live_trades[stock_name]
            
            elif live_price <= trade["SL"]:
                trade["Status"] = "SL Hit ❌"
                trade["Exit_Time"] = current_time_str
                trade["Exit_Price"] = live_price
                st.session_state.trade_history.append(trade)
                del st.session_state.active_live_trades[stock_name]

    # DISPLAY ACTIVE TRADES
    if st.session_state.active_live_trades:
        for stock, t in st.session_state.active_live_trades.items():
            current_pnl = round((t["Current_LTP"] - t["Entry"]) * t["Qty"], 2)
            pnl_text = f"🟢 +₹{current_pnl}" if current_pnl >= 0 else f"🔴 -₹{abs(current_pnl)}"
            
            card_text = (
                f"**{t['Stock']}** | <span class='strat-tag'>{t['Strategy']}</span> | {t['Action']} | Qty: `{t['Qty']}`\n\n"
                f"🕒 **Entry Time:** `{t['Entry_Time']}` | Entry Price: `₹{t['Entry']}`\n\n"
                f"⚡ **Live LTP: `₹{t['Current_LTP']}`** | 🛑 SL: `₹{t['SL']}` | 🚀 Target: `₹{t['Target']}`\n\n"
                f"Live P&L: **{pnl_text}**"
            )
            if current_pnl >= 0:
                st.success(card_text, icon="📈")
            else:
                st.warning(card_text, icon="📉")
    else:
        st.write("🔍 Scanning market... Waiting for strictly real strategy conditions to match.")

    # DISPLAY CLOSED TRADES
    st.markdown("---")
    st.subheader("📋 Closed Trades (Real Timestamps)")
    if st.session_state.trade_history:
        for t in reversed(st.session_state.trade_history):
            final_pnl = round((t["Exit_Price"] - t["Entry"]) * t["Qty"], 2)
            pnl_text = f"🟢 +₹{final_pnl}" if final_pnl >= 0 else f"🔴 -₹{abs(final_pnl)}"
            
            hist_text = (
                f"**{t['Stock']}** | Strategy: **{t['Strategy']}** | {t['Action']} \n\n"
                f"🕒 **Entry:** `{t['Entry_Time']}` @ `₹{t['Entry']}` \n\n"
                f"🕒 **Exit:** `{t['Exit_Time']}` @ `₹{t['Exit_Price']}` \n\n"
                f"Status: **{t['Status']}** | Final P&L: **{pnl_text}**"
            )
            if "Target" in t["Status"]:
                st.info(hist_text, icon="✅")
            else:
                st.error(hist_text, icon="❌")
    else:
        st.write("No trades completed yet.")

pure_live_scanner()
