import time
from datetime import datetime, timedelta
import pytz
import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Live Intraday Engine - Real Data", layout="wide")

# Custom CSS for compact mobile layout
st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
    h1 { font-size: 20px !important; margin-bottom: 0px !important; }
    h2 { font-size: 16px !important; margin-top: 5px !important; }
    p, div, span, label { font-size: 13px !important; }
    hr { margin: 10px 0px !important; }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Live Intraday Engine (Real Market Data)")
st.markdown("Fetching **Real-Time Prices** from NSE | Quantity: **10 Shares**")

# Real NSE Stock Symbols for yfinance
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

def get_current_date():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime("%Y-%m-%d")

# Session states to store active live trades
if "active_live_trades" not in st.session_state:
    st.session_state.active_live_trades = {}

if "trade_history" not in st.session_state:
    st.session_state.trade_history = []

def fetch_live_price(symbol):
    """Fetches real-time market price using yfinance"""
    try:
        ticker = yf.Ticker(symbol)
        # fast_info gets the most recent live price quickly
        return round(ticker.fast_info.last_price, 2)
    except Exception as e:
        return None

@st.fragment(run_every=30)
def live_market_scanner():
    now_ist = get_ist_time()
    st.info(f"🔄 **Engine Status:** 🟢 LIVE MARKET FEED | Last Sync: **{now_ist.strftime('%H:%M:%S')} IST**")
    
    st.subheader("📡 Real-Time Stock Tracker & Active Trades")
    
    # 1. Fetch live prices and generate entry if no active trade exists
    for stock_name, symbol in STOCKS.items():
        live_price = fetch_live_price(symbol)
        
        if live_price is not None:
            # Agar is stock ka trade nahi chal raha, toh Naya Trade lo REAL price par
            if stock_name not in st.session_state.active_live_trades:
                entry_price = live_price
                sl_price = round(entry_price - (entry_price * 0.005), 2) # 0.5% SL
                target_price = round(entry_price + (entry_price * 0.01), 2) # 1% Target
                
                st.session_state.active_live_trades[stock_name] = {
                    "Time": now_ist.strftime("%H:%M:%S"),
                    "Stock": stock_name,
                    "Action": "LONG (BUY)",
                    "Qty": TEST_QUANTITY,
                    "Entry": entry_price,
                    "Current_LTP": live_price,
                    "SL": sl_price,
                    "Target": target_price,
                    "Status": "Running ⏳"
                }
            else:
                # Agar trade chal raha hai, toh current LTP update karo
                trade = st.session_state.active_live_trades[stock_name]
                trade["Current_LTP"] = live_price
                
                # Check SL or Target Hit based on REAL live price
                if live_price <= trade["SL"]:
                    trade["Status"] = "SL Hit ❌"
                    trade["Exit"] = live_price
                    st.session_state.trade_history.append(trade)
                    del st.session_state.active_live_trades[stock_name]
                elif live_price >= trade["Target"]:
                    trade["Status"] = "Target Hit ✅"
                    trade["Exit"] = live_price
                    st.session_state.trade_history.append(trade)
                    del st.session_state.active_live_trades[stock_name]

    # 2. Display Active Trades in Card Layout (Mobile Friendly)
    if st.session_state.active_live_trades:
        for stock, t in st.session_state.active_live_trades.items():
            current_pnl = round((t["Current_LTP"] - t["Entry"]) * t["Qty"], 2)
            pnl_text = f"🟢 +₹{current_pnl}" if current_pnl >= 0 else f"🔴 -₹{abs(current_pnl)}"
            
            card_text = (
                f"🕒 Entry: `{t['Time']}` | **{t['Stock']}** | {t['Action']} | Qty: `{t['Qty']}`\n\n"
                f"🎯 Entry: `₹{t['Entry']}` | ⚡ **Live LTP: `₹{t['Current_LTP']}`**\n\n"
                f"🛑 SL: `₹{t['SL']}` | 🚀 Target: `₹{t['Target']}`\n\n"
                f"Live P&L: **{pnl_text}**"
            )
            if current_pnl >= 0:
                st.success(card_text)
            else:
                st.warning(card_text)
    else:
        st.write("No active trades currently.")

    # 3. Display Closed Trades History
    st.markdown("---")
    st.subheader("📋 Closed Trades History")
    if st.session_state.trade_history:
        for t in reversed(st.session_state.trade_history):
            final_pnl = round((t["Exit"] - t["Entry"]) * t["Qty"], 2)
            pnl_text = f"🟢 +₹{final_pnl}" if final_pnl >= 0 else f"🔴 -₹{abs(final_pnl)}"
            
            hist_text = (
                f"**{t['Stock']}** | Entry: `₹{t['Entry']}` | Exit: `₹{t['Exit']}` | "
                f"Status: **{t['Status']}** | Final P&L: **{pnl_text}**"
            )
            if "Target" in t["Status"]:
                st.info(hist_text)
            else:
                st.error(hist_text)
    else:
        st.write("No trades closed yet.")

live_market_scanner()
