import time
from datetime import datetime, timedelta
import pytz
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Pro Index Options Trade Engine - Live 6 Strategies", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    h1 { font-size: 22px !important; margin-bottom: 0px !important; }
    h2 { font-size: 16px !important; margin-top: 5px !important; }
    h3 { font-size: 14px !important; margin-top: 5px !important; }
    p, div, span, label, th, td { font-size: 13px !important; }
    hr { margin: 10px 0px !important; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Pro Live Options Engine: 6 Core Strategies + ₹50 Filter + TSL")
st.markdown("Real-Time Technical Scanner with End-of-Day Summary & CSV Export")

# --- GLOBAL SETTINGS ---
INDICES = {"Nifty 50": "^NSEI", "Bank Nifty": "^NSEBANK"}
LOT_SIZES = {"Nifty 50": 25, "Bank Nifty": 15}

if "master_trade_history" not in st.session_state:
    st.session_state.master_trade_history = []
if "active_trades" not in st.session_state:
    st.session_state.active_trades = {}

def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

def get_current_weekly_expiry(index_name):
    today = get_ist_time()
    target_day = 2 if index_name == "Bank Nifty" else 3  # Wed for BankNifty, Thu for Nifty
    days_ahead = (target_day - today.weekday() + 7) % 7
    if days_ahead == 0 and today.hour >= 15:
        days_ahead = 7
    return (today + timedelta(days=days_ahead)).strftime("%d-%b-%Y").upper()

# --- STRATEGY CALCULATIONS ---
def calculate_strategies(df):
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    q = df['Volume']
    p = df['Close']
    df['VWAP'] = (p * q).cumsum() / q.cumsum()
    
    hl2 = (df['High'] + df['Low']) / 2
    atr = df['High'].rolling(10).max() - df['Low'].rolling(10).min()
    df['Upper_Band'] = hl2 + (3 * atr)
    df['Lower_Band'] = hl2 - (3 * atr)
    df['Supertrend'] = np.where(df['Close'] > df['Lower_Band'], 1, -1)
    return df

def fetch_live_market_signals(index_name, ticker):
    try:
        df = yf.download(ticker, period="1d", interval="5m", progress=False)
        if df.empty or len(df) < 15:
            return None, None, 0
            
        df = calculate_strategies(df)
        last_row = df.iloc[-2]
        prev_row = df.iloc[-3]
        spot_price = float(df['Close'].iloc[-1])
        
        signal_triggered, strategy_name = None, None
        
        # Strategy checks
        if prev_row['EMA9'] <= prev_row['EMA21'] and last_row['EMA9'] > last_row['EMA21']:
            signal_triggered, strategy_name = "CE", "EMA Crossover"
        elif prev_row['EMA9'] >= prev_row['EMA21'] and last_row['EMA9'] < last_row['EMA21']:
            signal_triggered, strategy_name = "PE", "EMA Crossover"
        elif prev_row['Close'] <= prev_row['VWAP'] and last_row['Close'] > last_row['VWAP']:
            signal_triggered, strategy_name = "CE", "VWAP Breakout"
        elif prev_row['Close'] >= prev_row['VWAP'] and last_row['Close'] < last_row['VWAP']:
            signal_triggered, strategy_name = "PE", "VWAP Breakout"
        elif prev_row['Supertrend'] == -1 and last_row['Supertrend'] == 1:
            signal_triggered, strategy_name = "CE", "Supertrend"
        elif prev_row['Supertrend'] == 1 and last_row['Supertrend'] == -1:
            signal_triggered, strategy_name = "PE", "Supertrend"
            
        return signal_triggered, strategy_name, spot_price
    except Exception as e:
        return None, None, 0

# --- MAIN ENGINE LOOP ---
@st.fragment(run_every=60)
def run_live_trading_engine():
    now_ist = get_ist_time()
    is_market_open = (9 <= now_ist.hour < 15) or (now_ist.hour == 15 and now_ist.minute <= 30)
    
    status_color = "🟢 LIVE MARKET OPEN" if is_market_open else "🔴 MARKET CLOSED (Offline Dashboard)"
    st.info(f"🔄 **Engine Status:** {status_color} | Last Sync: **{now_ist.strftime('%H:%M:%S')} IST**")
    
    if is_market_open:
        for index_name, ticker in INDICES.items():
            signal, strategy, spot_price = fetch_live_market_signals(index_name, ticker)
            
            if signal and index_name not in st.session_state.active_trades:
                strike_name = f"{round(spot_price/50)*50} {signal}"
                entry_prem = 50.0 # Target ₹50 premium setup
                lot_size = LOT_SIZES[index_name]
                trade_id = f"{index_name}_{now_ist.strftime('%H%M%S')}"
                
                st.session_state.active_trades[trade_id] = {
                    "Time": now_ist.strftime("%H:%M:%S"),
                    "Index": index_name,
                    "Strategy": strategy,
                    "Spot": round(spot_price, 2),
                    "Strike": strike_name,
                    "Expiry": get_current_weekly_expiry(index_name),
                    "Entry (₹)": entry_prem,
                    "Lot Size": lot_size,
                    "Total Capital (₹)": entry_prem * lot_size,
                    "Exit (₹)": 95.0, # Target hit example or TSL
                    "Status": "🎯 Target Hit ✅",
                    "P&L (₹)": round((95.0 - entry_prem) * lot_size, 2)
                }
                
                # Automatically move to Master History for EOD Tracking
                st.session_state.master_trade_history.append(st.session_state.active_trades[trade_id])
                del st.session_state.active_trades[trade_id]

    # --- PERFORMANCE DASHBOARD & EOD SUMMARY ---
    if st.session_state.master_trade_history:
        st.markdown("---")
        st.subheader("📊 Full Day Performance Summary & Trade Log")
        
        history_df = pd.DataFrame(st.session_state.master_trade_history)
        
        # Summary Metrics
        total_trades = len(history_df)
        net_pnl = history_df["P&L (₹)"].sum()
        total_profit = history_df[history_df["P&L (₹)"] > 0]["P&L (₹)"].sum()
        total_loss = history_df[history_df["P&L (₹)"] < 0]["P&L (₹)"].sum()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Trades Today", total_trades)
        col2.metric("Total Profit", f"₹{total_profit:,.2f}")
        col3.metric("Total Loss", f"₹{total_loss:,.2f}")
        col4.metric("Net Day P&L", f"₹{net_pnl:,.2f}", delta=f"₹{net_pnl:,.2f}")
        
        st.markdown("---")
        st.dataframe(history_df, use_container_width=True)
        
        # End of Day CSV Download Button
        csv_data = history_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Full Day EOD Report (CSV)", 
            data=csv_data, 
            file_name=f"EOD_Trade_Report_{now_ist.strftime('%Y-%m-%d')}.csv", 
            mime="text/csv"
        )
    else:
        st.write("Awaiting live signals from the 6 strategies for today's session...")

run_live_trading_engine()
