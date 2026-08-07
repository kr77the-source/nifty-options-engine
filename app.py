import time
from datetime import datetime, timedelta
import pytz
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Top 5 F&O Gainers/Losers Engine", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; }
    h1 { font-size: 18px !important; margin-bottom: 0px !important; }
    h2 { font-size: 14px !important; margin-top: 2px !important; margin-bottom: 2px !important; }
    p, div, span, label { font-size: 12px !important; }
    hr { margin: 5px 0px !important; }
    .strat-tag { font-weight: bold; color: #00FF7F; }
    .gainer { color: #00FF00; font-weight: bold; }
    .loser { color: #FF4500; font-weight: bold; }
    .compact-box { margin-bottom: 4px; line-height: 1.2; }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 F&O Momentum Engine (Top 5 Gainers & Losers)")
st.markdown("Strictly Real-Time | **Live Stock Screener + 4-Indicator Confluence** | Qty: 10 Shares")

# Expanded list of highly liquid F&O Stocks for scanning
FO_STOCKS = {
    "Reliance": "RELIANCE.NS", "HDFC Bank": "HDFCBANK.NS", "ICICI Bank": "ICICIBANK.NS",
    "Infosys": "INFY.NS", "TCS": "TCS.NS", "SBI": "SBIN.NS", 
    "Bharti Airtel": "BHARTIARTL.NS", "ITC": "ITC.NS", "L&T": "LT.NS",
    "Tata Motors": "TATAMOTORS.NS", "Axis Bank": "AXISBANK.NS", "Maruti": "MARUTI.NS",
    "Sun Pharma": "SUNPHARMA.NS", "Tata Steel": "TATASTEEL.NS", "M&M": "M&M.NS",
    "HUL": "HINDUNILVR.NS", "Power Grid": "POWERGRID.NS", "NTPC": "NTPC.NS",
    "Bajaj Finance": "BAJFINANCE.NS", "Asian Paints": "ASIANPAINT.NS"
}
TEST_QUANTITY = 10

def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

# Session States
if "active_live_trades" not in st.session_state:
    st.session_state.active_live_trades = {}
if "trade_history" not in st.session_state:
    st.session_state.trade_history = {}

def get_top_gainers_losers():
    """Scans the F&O list to find Top 5 Gainers and Top 5 Losers dynamically with safety checks"""
    tickers = list(FO_STOCKS.values())
    try:
        data = yf.download(tickers, period="1d", interval="1m", group_by="ticker", progress=False)
        performance = []
        
        for name, symbol in FO_STOCKS.items():
            try:
                if symbol in data and not data[symbol].empty:
                    df = data[symbol].dropna()
                    if len(df) > 0:
                        open_price = float(df['Open'].iloc[0])
                        current_price = float(df['Close'].iloc[-1])
                        if open_price > 0:
                            pct_change = ((current_price - open_price) / open_price) * 100
                            performance.append({"Stock": name, "Symbol": symbol, "Change": pct_change, "LTP": current_price})
            except Exception:
                continue
        
        if not performance:
            return [], []
            
        performance = sorted(performance, key=lambda x: x['Change'], reverse=True)
        top_5_gainers = performance[:5]
        top_5_losers = performance[-5:]
        
        return top_5_gainers, top_5_losers
    except Exception as e:
        return [], []

def calculate_strict_technicals(df):
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['Vol_Avg_20'] = df['Volume'].rolling(window=20).mean()
    return df

def get_high_accuracy_signal(symbol, trend_type):
    try:
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        if df.empty or len(df) < 30: return "NONE", None, ""
        
        df = calculate_strict_technicals(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        ltp = round(float(last['Close']), 2)
        
        high_volume = last['Volume'] > last['Vol_Avg_20']

        if trend_type == "GAINER":
            ema_cross = last['EMA_9'] > last['EMA_21'] and prev['EMA_9'] <= prev['EMA_21']
            vwap_trend = last['Close'] > last['VWAP']
            rsi_strong = 55 < last['RSI'] < 75
            
            if ema_cross and vwap_trend and rsi_strong and high_volume:
                return "LONG", ltp, "Super Confluence (Buy)"

        elif trend_type == "LOSER":
            ema_cross_down = last['EMA_9'] < last['EMA_21'] and prev['EMA_9'] >= prev['EMA_21']
            vwap_downtrend = last['Close'] < last['VWAP']
            rsi_weak = 25 < last['RSI'] < 45
            
            if ema_cross_down and vwap_downtrend and rsi_weak and high_volume:
                return "SHORT", ltp, "Super Confluence (Sell)"
                
        return "NONE", ltp, ""
    except Exception:
        return "NONE", None, ""

@st.fragment(run_every=45)
def pure_live_scanner():
    now_ist = get_ist_time()
    current_time_str = now_ist.strftime('%H:%M:%S')
    
    st.info(f"🔄 **Engine Sync:** {current_time_str} IST | Scanning Top Movers...")
    
    gainers, losers = get_top_gainers_losers()
    
    # SINGLE LINE FORMAT FOR GAINERS
    st.markdown("📈 **Top 5 Gainers (LONG):**", unsafe_allow_html=True)
    if gainers:
        gainer_str = " | ".join([f"<span class='gainer'>{g['Stock']} +{g['Change']:.2f}% (₹{g['LTP']:.2f})</span>" for g in gainers])
        st.markdown(f"<div class='compact-box'>{gainer_str}</div>", unsafe_allow_html=True)
    else:
        st.write("Fetching gainers data...")
        
    st.markdown("---")
    
    # SINGLE LINE FORMAT FOR LOSERS
    st.markdown("📉 **Top 5 Losers (SHORT):**", unsafe_allow_html=True)
    if losers:
        loser_str = " | ".join([f"<span class='loser'>{l['Stock']} {l['Change']:.2f}% (₹{l['LTP']:.2f})</span>" for l in losers])
        st.markdown(f"<div class='compact-box'>{loser_str}</div>", unsafe_allow_html=True)
    else:
        st.write("Fetching losers data...")
        
    st.markdown("---")
    st.subheader("📡 Live Signals & Active Trades (10 Shares)")
    
    target_stocks = [(g['Stock'], g['Symbol'], "GAINER") for g in gainers] + [(l['Stock'], l['Symbol'], "LOSER") for l in losers]
    
    for stock_name, symbol, trend_type in target_stocks:
        signal, live_price, strat_name = get_high_accuracy_signal(symbol, trend_type)
        
        if live_price is not None and stock_name not in st.session_state.active_live_trades:
            if signal in ["LONG", "SHORT"]:
                entry_price = live_price
                if signal == "LONG":
                    sl_price = round(entry_price - (entry_price * 0.005), 2)  
                    target_price = round(entry_price + (entry_price * 0.01), 2)
                else: 
                    sl_price = round(entry_price + (entry_price * 0.005), 2)  
                    target_price = round(entry_price - (entry_price * 0.01), 2)
                
                st.session_state.active_live_trades[stock_name] = {
                    "Entry_Time": current_time_str,
                    "Stock": stock_name,
                    "Strategy": strat_name,
                    "Action": f"{signal} {'(BUY)' if signal=='LONG' else '(SELL)'}",
                    "Qty": TEST_QUANTITY,
                    "Entry": entry_price,
                    "Current_LTP": live_price,
                    "SL": sl_price,
                    "Target": target_price,
                    "Status": "Running ⏳",
                    "Exit_Time": "--",
                    "Type": signal
                }
                
        elif stock_name in st.session_state.active_live_trades and live_price is not None:
            trade = st.session_state.active_live_trades[stock_name]
            trade["Current_LTP"] = live_price
            
            is_long = trade["Type"] == "LONG"
            target_hit = (is_long and live_price >= trade["Target"]) or (not is_long and live_price <= trade["Target"])
            sl_hit = (is_long and live_price <= trade["SL"]) or (not is_long and live_price >= trade["SL"])
            
            if target_hit:
                trade["Status"] = "Target Hit ✅"
                trade["Exit_Time"] = current_time_str
                trade["Exit_Price"] = live_price
                st.session_state.trade_history[stock_name + current_time_str] = trade
                del st.session_state.active_live_trades[stock_name]
            
            elif sl_hit:
                trade["Status"] = "SL Hit ❌"
                trade["Exit_Time"] = current_time_str
                trade["Exit_Price"] = live_price
                st.session_state.trade_history[stock_name + current_time_str] = trade
                del st.session_state.active_live_trades[stock_name]

    if st.session_state.active_live_trades:
        for stock, t in st.session_state.active_live_trades.items():
            multiplier = 1 if t["Type"] == "LONG" else -1
            current_pnl = round((t["Current_LTP"] - t["Entry"]) * t["Qty"] * multiplier, 2)
            pnl_text = f"🟢 +₹{current_pnl}" if current_pnl >= 0 else f"🔴 -₹{abs(current_pnl)}"
            
            card_text = (
                f"**{t['Stock']}** | <span class='strat-tag'>{t['Strategy']}</span> | **{t['Action']}** | Qty: `{t['Qty']}`\n\n"
                f"🕒 **Entry Time:** `{t['Entry_Time']}` | Entry Price: `₹{t['Entry']}`\n\n"
                f"⚡ **Live LTP: `₹{t['Current_LTP']}`** | 🛑 SL: `₹{t['SL']}` | 🚀 Target: `₹{t['Target']}`\n\n"
                f"Live P&L: **{pnl_text}**"
            )
            st.success(card_text, icon="📈") if current_pnl >= 0 else st.warning(card_text, icon="📉")
    else:
        st.write("🔍 Scanning market... Waiting for strictly real high-accuracy setup on Top Movers.")

pure_live_scanner()
