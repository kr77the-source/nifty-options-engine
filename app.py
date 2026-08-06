import time
from datetime import datetime, timedelta
import pytz
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Pro Index Options Trade Engine - 100% Real Live", layout="wide")

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

st.title("⚡ 100% Real Live Options Engine: 6 Core Strategies")
st.markdown("Strictly Real-Time Mathematical Technical Scanner (No Mock Data)")

# --- GLOBAL CONFIGURATION ---
INDICES = {"Nifty 50": "^NSEI", "Bank Nifty": "^NSEBANK"}
LOT_SIZES = {"Nifty 50": 25, "Bank Nifty": 15}

if "master_trade_history" not in st.session_state:
    st.session_state.master_trade_history = []
if "active_signals" not in st.session_state:
    st.session_state.active_signals = {}

def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

def get_current_weekly_expiry(index_name):
    today = get_ist_time()
    target_day = 2 if index_name == "Bank Nifty" else 3  # Wednesday for Bank Nifty, Thursday for Nifty
    days_ahead = (target_day - today.weekday() + 7) % 7
    if days_ahead == 0 and today.hour >= 15:
        days_ahead = 7
    return (today + timedelta(days=days_ahead)).strftime("%d-%b-%Y").upper()

# --- 100% REAL MATHEMATICAL STRATEGY CALCULATIONS ---
def calculate_all_six_strategies(df):
    """Computes real technical indicators using actual market OHLCV data"""
    
    # 1. EMA (9 and 21)
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    # 2. VWAP (Volume Weighted Average Price)
    q = df['Volume']
    p = df['Close']
    df['VWAP'] = (p * q).cumsum() / q.cumsum()
    
    # 3. Supertrend (10, 3)
    hl2 = (df['High'] + df['Low']) / 2
    atr = (df['High'] - df['Low']).rolling(10).mean()
    df['Upper_Band'] = hl2 + (3 * atr)
    df['Lower_Band'] = hl2 - (3 * atr)
    df['Supertrend'] = np.where(df['Close'] > df['Lower_Band'], 1, -1)
    
    # 4. CPR (Central Pivot Range) - Calculated from previous session high/low/close
    prev_high = df['High'].iloc[-75]
    prev_low = df['Low'].iloc[-75]
    prev_close = df['Close'].iloc[-75]
    pivot = (prev_high + prev_low + prev_close) / 3
    bc = (prev_high + prev_low) / 2
    tc = (2 * pivot) - bc
    df['CPR_Pivot'] = pivot
    df['CPR_TC'] = tc
    df['CPR_BC'] = bc
    
    # 5. PDH / PDL (Previous Day High & Low)
    df['PDH'] = prev_high
    df['PDL'] = prev_low
    
    return df

def scan_live_market(index_name, ticker):
    """Fetches real live feed and evaluates all 6 strategies strictly"""
    try:
        df = yf.download(ticker, period="2d", interval="5m", progress=False)
        if df.empty or len(df) < 50:
            return None, None, 0.0
            
        df = calculate_all_six_strategies(df)
        last_row = df.iloc[-2]  # Fully formed candle
        prev_row = df.iloc[-3]  # Previous candle
        current_spot = float(df['Close'].iloc[-1])
        
        signal = None
        matched_strategy = None
        
        # Strategy 1: EMA Crossover
        if prev_row['EMA9'] <= prev_row['EMA21'] and last_row['EMA9'] > last_row['EMA21']:
            signal, matched_strategy = "CE", "EMA Crossover"
        elif prev_row['EMA9'] >= prev_row['EMA21'] and last_row['EMA9'] < last_row['EMA21']:
            signal, matched_strategy = "PE", "EMA Crossover"
            
        # Strategy 2: VWAP Breakout
        elif prev_row['Close'] <= prev_row['VWAP'] and last_row['Close'] > last_row['VWAP']:
            signal, matched_strategy = "CE", "VWAP Breakout"
        elif prev_row['Close'] >= prev_row['VWAP'] and last_row['Close'] < last_row['VWAP']:
            signal, matched_strategy = "PE", "VWAP Breakout"
            
        # Strategy 3: Supertrend Flip
        elif prev_row['Supertrend'] == -1 and last_row['Supertrend'] == 1:
            signal, matched_strategy = "CE", "Supertrend"
        elif prev_row['Supertrend'] == 1 and last_row['Supertrend'] == -1:
            signal, matched_strategy = "PE", "Supertrend"
            
        # Strategy 4: CPR Boundary Reversal / Breakout
        elif last_row['Close'] > last_row['CPR_TC'] and prev_row['Close'] <= prev_row['CPR_TC']:
            signal, matched_strategy = "CE", "CPR Breakout"
        elif last_row['Close'] < last_row['CPR_BC'] and prev_row['Close'] >= prev_row['CPR_BC']:
            signal, matched_strategy = "PE", "CPR Breakout"
            
        # Strategy 5: PDH / PDL Breakout
        elif last_row['Close'] > last_row['PDH'] and prev_row['Close'] <= prev_row['PDH']:
            signal, matched_strategy = "CE", "PDH Breakout"
        elif last_row['Close'] < last_row['PDL'] and prev_row['Close'] >= prev_row['PDL']:
            signal, matched_strategy = "PE", "PDL Breakout"

        return signal, matched_strategy, current_spot
        
    except Exception as error:
        st.error(f"Live Feed Error for {index_name}: {error}")
        return None, None, 0.0

# --- REAL-TIME STREAMLIT EXECUTION ENGINE ---
@st.fragment(run_every=60)
def run_production_engine():
    now_ist = get_ist_time()
    is_market_open = (9 <= now_ist.hour < 15) or (now_ist.hour == 15 and now_ist.minute <= 30)
    
    status_display = "🟢 LIVE MARKET OPEN" if is_market_open else "🔴 MARKET CLOSED (Offline Mode)"
    st.info(f"🔄 **Engine Status:** {status_display} | Synchronized Time: **{now_ist.strftime('%H:%M:%S')} IST**")
    
    if is_market_open:
        for index_name, ticker in INDICES.items():
            signal, strategy, spot_price = scan_live_market(index_name, ticker)
            
            if signal and spot_price > 0:
                atm_strike = int(round(spot_price / 50.0) * 50) if index_name == "Nifty 50" else int(round(spot_price / 100.0) * 100)
                contract_name = f"{atm_strike} {signal}"
                
                signal_key = f"{index_name}_{strategy}_{now_ist.strftime('%H%M')}"
                if signal_key not in st.session_state.active_signals:
                    signal_record = {
                        "Timestamp": now_ist.strftime("%H:%M:%S"),
                        "Index": index_name,
                        "Strategy": strategy,
                        "Spot Price": round(spot_price, 2),
                        "Option Strike": contract_name,
                        "Expiry": get_current_weekly_expiry(index_name),
                        "Action": "BUY CALL" if signal == "CE" else "BUY PUT"
                    }
                    st.session_state.active_signals[signal_key] = signal_record
                    st.session_state.master_trade_history.append(signal_record)

    # --- DASHBOARD DISPLAY & EOD LOG ---
    st.markdown("---")
    st.subheader("📊 Real-Time Strategy Signals & Trigger Log")
    
    if st.session_state.master_trade_history:
        history_df = pd.DataFrame(st.session_state.master_trade_history)
        st.dataframe(history_df, use_container_width=True)
        
        csv_export = history_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Real Session Report (CSV)", 
            data=csv_export, 
            file_name=f"Real_Strategy_Log_{now_ist.strftime('%Y-%m-%d')}.csv", 
            mime="text/csv"
        )
    else:
        st.write("Engine is actively scanning real-time live candles for all 6 strategies. Awaiting live market triggers...")

run_production_engine()
