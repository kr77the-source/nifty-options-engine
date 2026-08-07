import time
from datetime import datetime, timedelta
import pytz
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Advanced Multi-Strategy Live Scanner & Backtest", layout="wide")

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
    .market-status { background-color: #1e293b; padding: 8px; border-radius: 6px; margin-bottom: 10px; font-weight: bold; color: #38bdf8; text-align: center; font-size: 14px !important; }
    .compact-box { margin-bottom: 4px; line-height: 1.2; }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 Advanced Multi-Strategy Momentum Engine + Morning Backtest")
st.markdown("Strictly Real-Time | **Live Status + Top Movers + Morning Replay Simulation**")

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
                            pos_text = "High" if current_price > prev_high else ("Low" if current_price < prev_low else "Sideways")
                            indices_status.append({"Stock": name, "Symbol": symbol, "Change": pct_change, "LTP": current_price, "Status": pos_text})
                            
                        performance.append({"Stock": name, "Symbol": symbol, "Change": pct_change, "LTP": current_price})
            except Exception:
                continue
        
        if not performance:
            return [], [], [], "Nifty: Sideways | Bank Nifty: Sideways"
            
        performance = sorted(performance, key=lambda x: x['Change'], reverse=True)
        stock_performance = [p for p in performance if p['Symbol'] not in ["^NSEI", "^NSEBANK"]]
        
        top_5_gainers = stock_performance[:5]
        top_5_losers = stock_performance[-5:]
        
        nifty_item = next((i for i in indices_status if i['Symbol'] == "^NSEI"), None)
        bank_item = next((i for i in indices_status if i['Symbol'] == "^NSEBANK"), None)
        
        market_summary = f"Nifty: {nifty_item['Status'] if nifty_item else 'Sideways'} | Bank Nifty: {bank_item['Status'] if bank_item else 'Sideways'}"
        return top_5_gainers, top_5_losers, indices_status, market_summary
    except Exception:
        return [], [], [], "Nifty: Sideways | Bank Nifty: Sideways"

def calculate_all_strategies(df):
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
    
    hl2 = (df['High'] + df['Low']) / 2
    tr = pd.concat([df['High'] - df['Low'], abs(df['High'] - df['Close'].shift(1)), abs(df['Low'] - df['Close'].shift(1))], axis=1).max(axis=1)
    atr = tr.rolling(window=10).mean()
    df['ST_Upper'] = hl2 + (3 * atr)
    df['ST_Lower'] = hl2 - (3 * atr)
    df['Supertrend'] = 1
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > df['ST_Upper'].iloc[i-1]: df.loc[df.index[i], 'Supertrend'] = 1
        elif df['Close'].iloc[i] < df['ST_Lower'].iloc[i-1]: df.loc[df.index[i], 'Supertrend'] = -1
        else: df.loc[df.index[i], 'Supertrend'] = df['Supertrend'].iloc[i-1]

    if len(df) >= 15:
        df['ORB_High'] = df['High'].iloc[:15].max()
        df['ORB_Low'] = df['Low'].iloc[:15].min()
    else:
        df['ORB_High'] = df['High'].iloc[0]
        df['ORB_Low'] = df['Low'].iloc[0]
    return df

def run_morning_backtest_simulation(symbol, trend_type):
    try:
        df = yf.download(symbol, period="1d", interval="1m", progress=False)
        if df.empty or len(df) < 35: return []
        df = calculate_all_strategies(df)
        
        simulated_trades = []
        in_trade = False
        trade_obj = {}
        
        for i in range(30, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i-1]
            t_time = df.index[i].strftime('%H:%M')
            price = float(row['Close'])
            vol_check = True if symbol in ["^NSEI", "^NSEBANK"] else (row['Volume'] > (row['Vol_Avg_20'] * 1.5))
            
            if not in_trade:
                signal, strat = "NONE", ""
                if trend_type == "BULLISH":
                    if row['EMA_9'] > row['EMA_21'] and prev['EMA_9'] <= prev['EMA_21']: signal, strat = "LONG", "EMA Crossover"
                    elif row['Close'] > row['VWAP'] and prev['Close'] <= prev['VWAP']: signal, strat = "LONG", "VWAP Bounce"
                    elif row['MACD'] > row['Signal_Line'] and prev['MACD'] <= prev['Signal_Line']: signal, strat = "LONG", "MACD Breakout"
                    elif row['Supertrend'] == 1 and prev['Supertrend'] == -1: signal, strat = "LONG", "Supertrend Buy"
                    elif row['Close'] > row['ORB_High'] and prev['Close'] <= prev['ORB_High']: signal, strat = "LONG", "ORB Breakout"
                else:
                    if row['EMA_9'] < row['EMA_21'] and prev['EMA_9'] >= prev['EMA_21']: signal, strat = "SHORT", "EMA Crossover"
                    elif row['Close'] < row['VWAP'] and prev['Close'] >= prev['VWAP']: signal, strat = "SHORT", "VWAP Breakdown"
                    elif row['MACD'] < row['Signal_Line'] and prev['MACD'] >= prev['Signal_Line']: signal, strat = "SHORT", "MACD Breakdown"
                    elif row['Supertrend'] == -1 and prev['Supertrend'] == 1: signal, strat = "SHORT", "Supertrend Sell"
                    elif row['Close'] < row['ORB_Low'] and prev['Close'] >= prev['ORB_Low']: signal, strat = "SHORT", "ORB Breakdown"
                
                if signal in ["LONG", "SHORT"]:
                    in_trade = True
                    sl = round(price - (price * 0.003) if signal == "LONG" else price + (price * 0.003), 2)
                    tgt = round(price + (price * 0.006) if signal == "LONG" else price - (price * 0.006), 2)
                    trade_obj = {"Time": t_time, "Strategy": strat, "Type": signal, "Entry": price, "SL": sl, "Target": tgt}
            else:
                is_long = trade_obj["Type"] == "LONG"
                hit_tgt = (is_long and price >= trade_obj["Target"]) or (not is_long and price <= trade_obj["Target"])
                hit_sl = (is_long and price <= trade_obj["SL"]) or (not is_long and price >= trade_obj["SL"])
                
                if hit_tgt or hit_sl or i == len(df) - 1:
                    exit_price = price
                    pnl = round((exit_price - trade_obj["Entry"]) * TEST_QUANTITY * (1 if is_long else -1), 2)
                    trade_obj["Exit_Time"] = t_time
                    trade_obj["Exit_Price"] = exit_price
                    trade_obj["Result"] = "Target Hit ✅" if hit_tgt else ("SL Hit ❌" if hit_sl else "Closed LTP ⏳")
                    trade_obj["PnL"] = pnl
                    simulated_trades.append(trade_obj)
                    in_trade = False
        return simulated_trades
    except Exception:
        return []

@st.fragment(run_every=30)
def pure_live_scanner():
    now_ist = get_ist_time()
    current_time_str = now_ist.strftime('%H:%M:%S')
    
    st.info(f"🔄 **Engine Sync:** {current_time_str} IST | Scanning Live & Morning Backtest...")
    
    gainers, losers, indices_status, market_summary = get_market_data()
    st.markdown(f"<div class='market-status'>{market_summary}</div>", unsafe_allow_html=True)
    
    if indices_status:
        for ind in indices_status:
            color_class = 'gainer' if ind['Change'] >= 0 else 'loser'
            st.markdown(f"📊 **{ind['Stock']}**: <span class='{color_class}'>{'+' if ind['Change']>=0 else ''}{ind['Change']:.2f}% (₹{ind['LTP']:.2f})</span>", unsafe_allow_html=True)
        st.markdown("---")

    st.subheader("🌅 Morning-to-Now Backtest Simulation (Histo-Replay)")
    all_targets = [(i['Stock'], i['Symbol'], "BULLISH" if i['Change'] >= 0 else "BEARISH") for i in indices_status] + \
                  [(g['Stock'], g['Symbol'], "BULLISH") for g in gainers] + \
                  [(l['Stock'], l['Symbol'], "BEARISH") for l in losers]
    
    total_backtest_pnl = 0
    trade_count = 0
    
    for s_name, sym, t_type in all_targets[:8]:  # checking top items for performance speed
        sim_trades = run_morning_backtest_simulation(sym, t_type)
        for st_trade in sim_trades:
            trade_count += 1
            total_backtest_pnl += st_trade['PnL']
            pnl_color = "gainer" if st_trade['PnL'] >= 0 else "loser"
            st.markdown(f"• **{s_name}** | <span class='strat-tag'>{st_trade['Strategy']}</span> | {st_trade['Type']} | Entry: `₹{st_trade['Entry']}` at `{st_trade['Time']}` | Exit: `₹{st_trade['Exit_Price']}` ({st_trade['Result']}) | PnL: <span class='{pnl_color}'>₹{st_trade['PnL']}</span>", unsafe_allow_html=True)
            
    if trade_count == 0:
        st.write("No historical morning triggers matched the precise strategy parameters today so far.")
    else:
        net_color = "gainer" if total_backtest_pnl >= 0 else "loser"
        st.markdown(f"### Total Morning Simulation Net P&L: <span class='{net_color}'>₹{total_backtest_pnl}</span> across {trade_count} trades", unsafe_allow_html=True)

pure_live_scanner()
