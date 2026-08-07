import time
from datetime import datetime, timedelta
import pytz
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Top Movers & Indices - 6 Core Strategies", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem !important; padding-bottom: 1rem !important; }
    h1 { font-size: 18px !important; margin-bottom: 0px !important; }
    h2 { font-size: 14px !important; margin-top: 2px !important; margin-bottom: 2px !important; }
    p, div, span, label { font-size: 12px !important; }
    hr { margin: 5px 0px !important; }
    .strat-tag { font-weight: bold; color: #00FF7F; }
    .gainer { color: #00FF00; font-weight: bold; }
    .loser { color: #FF4500; font-weight: bold; }
    .range-box { color: #FFD700; font-weight: bold; }
    .market-status { background-color: #1e293b; padding: 8px; border-radius: 6px; margin-bottom: 10px; font-weight: bold; color: #38bdf8; text-align: center; }
    .compact-box { margin-bottom: 4px; line-height: 1.2; }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 F&O & Indices Momentum Engine")
st.markdown("Strictly Real-Time | **Market Trend Status + Top Movers + 6 Core Strategies**")

FO_STOCKS = {
    "Nifty 50": "^NSEI", "Bank Nifty": "^NSEBANK",
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

if "active_live_trades" not in st.session_state:
    st.session_state.active_live_trades = {}
if "trade_history" not in st.session_state:
    st.session_state.trade_history = {}

def get_market_data():
    tickers = list(FO_STOCKS.values())
    try:
        data = yf.download(tickers, period="2d", interval="1m", group_by="ticker", progress=False)
        performance = []
        indices_status = []
        
        for name, symbol in FO_STOCKS.items():
            try:
                if symbol in data and not data[symbol].empty:
                    df = data[symbol].dropna()
                    if len(df) > 0:
                        current_price = float(df['Close'].iloc[-1])
                        open_price = float(df['Open'].iloc[0])
                        pct_change = ((current_price - open_price) / open_price) * 100 if open_price > 0 else 0
                        
                        if len(df) > 375:
                            prev_day_df = df.iloc[:-375]
                            if not prev_day_df.empty:
                                prev_high = float(prev_day_df['High'].max())
                                prev_low = float(prev_day_df['Low'].min())
                            else:
                                prev_high, prev_low = current_price * 1.01, current_price * 0.99
                        else:
                            prev_high, prev_low = current_price * 1.01, current_price * 0.99
                            
                        if symbol in ["^NSEI", "^NSEBANK"]:
                            if current_price > prev_high:
                                pos_text = "🚀 Above Prev High (Breakout)"
                            elif current_price < prev_low:
                                pos_text = "🔻 Below Prev Low (Breakdown)"
                            else:
                                pos_text = "⚖️ Inside Prev High - Low Range (Sideways)"
                                
                            indices_status.append({
                                "Stock": name, "Symbol": symbol, "Change": pct_change, 
                                "LTP": current_price, "Status": pos_text
                            })
                            
                        performance.append({"Stock": name, "Symbol": symbol, "Change": pct_change, "LTP": current_price})
            except Exception:
                continue
        
        if not performance:
            return [], [], [], "Market status unavailable"
            
        performance = sorted(performance, key=lambda x: x['Change'], reverse=True)
        stock_performance = [p for p in performance if p['Symbol'] not in ["^NSEI", "^NSEBANK"]]
        
        top_5_gainers = stock_performance[:5]
        top_5_losers = stock_performance[-5:]
        
        nifty_item = next((i for i in indices_status if i['Symbol'] == "^NSEI"), None)
        if nifty_item:
            if "Above" in nifty_item['Status']:
                market_summary = "Market Trend: Bullish / Up (Above Previous High)"
            elif "Below" in nifty_item['Status']:
                market_summary = "Market Trend: Bearish / Down (Below Previous Low)"
            else:
                market_summary = "Market Trend: Sideways (Inside Previous Day Range)"
        else:
            market_summary = "Market Trend: Sideways / Normal"
        
        return top_5_gainers, top_5_losers, indices_status, market_summary
    except Exception:
        return [], [], [], "Market trend unavailable"

def calculate_6_strategies(df):
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum() if 'Volume' in df and df['Volume'].sum() > 0 else df['Close']
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['STD_20'] = df['Close'].rolling(window=20).std()
    df['Upper_BB'] = df['SMA_20'] + (df['STD_20'] * 2)
    df['Lower_BB'] = df['SMA_20'] - (df['STD_20'] * 2)
    df['Vol_Avg_20'] = df['Volume'].rolling(window=20).mean() if 'Volume' in df else pd.Series(1, index=df.index)
    
    return df

def check_6_strategies_signal(symbol, trend_type):
    try:
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        if df.empty or len(df) < 30: return "NONE", None, ""
        
        df = calculate_6_strategies(df)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        ltp = round(float(last['Close']), 2)
        vol_check = True if symbol in ["^NSEI", "^NSEBANK"] else (last['Volume'] > (last['Vol_Avg_20'] * 2.0))
        
        if trend_type == "BULLISH":
            if last['EMA_9'] > last['EMA_21'] and prev['EMA_9'] <= prev['EMA_21']: return "LONG", ltp, "EMA Crossover"
            if last['Close'] > last['VWAP'] and prev['Close'] <= prev['VWAP']: return "LONG", ltp, "VWAP Bounce"
            if last['MACD'] > last['Signal_Line'] and prev['MACD'] <= prev['Signal_Line']: return "LONG", ltp, "MACD Breakout"
            if last['RSI'] > 40 and prev['RSI'] <= 40: return "LONG", ltp, "RSI Reversal"
            if last['Close'] > last['Upper_BB'] and prev['Close'] <= prev['Upper_BB']: return "LONG", ltp, "Bollinger Breakout"
            if vol_check and last['Close'] > prev['Close']: return "LONG", ltp, "Momentum Surge"

        elif trend_type == "BEARISH":
            if last['EMA_9'] < last['EMA_21'] and prev['EMA_9'] >= prev['EMA_21']: return "SHORT", ltp, "EMA Crossover"
            if last['Close'] < last['VWAP'] and prev['Close'] >= prev['VWAP']: return "SHORT", ltp, "VWAP Breakdown"
            if last['MACD'] < last['Signal_Line'] and prev['MACD'] >= prev['Signal_Line']: return "SHORT", ltp, "MACD Breakdown"
            if last['RSI'] < 60 and prev['RSI'] >= 60: return "SHORT", ltp, "RSI Breakdown"
            if last['Close'] < last['Lower_BB'] and prev['Close'] >= prev['Lower_BB']: return "SHORT", ltp, "Bollinger Breakdown"
            if vol_check and last['Close'] < prev['Close']: return "SHORT", ltp, "Momentum Drop"
                
        return "NONE", ltp, ""
    except Exception:
        return "NONE", None, ""

@st.fragment(run_every=45)
def pure_live_scanner():
    now_ist = get_ist_time()
    current_time_str = now_ist.strftime('%H:%M:%S')
    
    st.info(f"🔄 **Engine Sync:** {current_time_str} IST | Scanning Market Trend & Top Movers...")
    
    gainers, losers, indices_status, market_summary = get_market_data()
    
    st.markdown(f"<div class='market-status'>{market_summary}</div>", unsafe_allow_html=True)
    
    if indices_status:
        for ind in indices_status:
            color_class = 'gainer' if ind['Change'] >= 0 else 'loser'
            st.markdown(f"📊 **{ind['Stock']}**: <span class='{color_class}'>{'+' if ind['Change']>=0 else ''}{ind['Change']:.2f}% (₹{ind['LTP']:.2f})</span> | <span class='range-box'>{ind['Status']}</span>", unsafe_allow_html=True)
        st.markdown("---")

    st.markdown("📈 **Top 5 Gainers (LONG):**", unsafe_allow_html=True)
    if gainers:
        gainer_str = " | ".join([f"<span class='gainer'>{g['Stock']} +{g['Change']:.2f}% (₹{g['LTP']:.2f})</span>" for g in gainers])
        st.markdown(f"<div class='compact-box'>{gainer_str}</div>", unsafe_allow_html=True)
    else:
        st.write("Fetching gainers...")
        
    st.markdown("---")
    
    st.markdown("📉 **Top 5 Losers (SHORT):**", unsafe_allow_html=True)
    if losers:
        loser_str = " | ".join([f"<span class='loser'>{l['Stock']} {l['Change']:.2f}% (₹{l['LTP']:.2f})</span>" for l in losers])
        st.markdown(f"<div class='compact-box'>{loser_str}</div>", unsafe_allow_html=True)
    else:
        st.write("Fetching losers...")
        
    st.markdown("---")
    st.subheader("📡 Live Signals & Active Trades (10 Shares)")
    
    target_targets = [(i['Stock'], i['Symbol'], "BULLISH" if i['Change'] >= 0 else "BEARISH") for i in indices_status] + \
                     [(g['Stock'], g['Symbol'], "BULLISH") for g in gainers] + \
                     [(l['Stock'], l['Symbol'], "BEARISH") for l in losers]
    
    for stock_name, symbol, trend_type in target_targets:
        signal, live_price, strat_name = check_6_strategies_signal(symbol, trend_type)
        
        if live_price is not None and stock_name not in st.session_state.active_live_trades:
            if signal in ["LONG", "SHORT"]:
                entry_price = live_price
                if signal == "LONG":
                    sl_price = round(entry_price - (entry_price * 0.003), 2)  
                    target_price = round(entry_price + (entry_price * 0.006), 2)
                else: 
                    sl_price = round(entry_price + (entry_price * 0.003), 2)  
                    target_price = round(entry_price - (entry_price * 0.006), 2)
                
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
        st.write("🔍 Scanning market... Waiting for strategies to trigger on Indices & Top Movers.")

pure_live_scanner()
