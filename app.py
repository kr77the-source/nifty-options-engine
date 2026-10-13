import pandas as pd
import streamlit as st
import yfinance as yf

# Streamlit Page Config
st.set_page_config(
    page_title="Live Option Chain Viewer", page_icon="📊", layout="centered"
)

st.title("📊 Live Option Chain Viewer")
st.write(
    "Stock ya Index aur Expiry select karke direct Option Chain table dekhein."
)

# Top F&O Indices & Stocks Database
STOCK_DATABASE = [
    "^NSEI",  # Nifty 50
    "^BSESN",  # Sensex
    "^NSEBANK",  # Bank Nifty
    "TCS.NS",
    "RELIANCE.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "INFY.NS",
    "SBIN.NS",
    "BAJFINANCE.NS",
    "MARUTI.NS",
]

# 1. Selection
col1, col2 = st.columns(2)
with col1:
    selected_symbol = st.selectbox("Stock / Index:", options=STOCK_DATABASE)
with col_inp2 if "col_inp2" in locals() else col2:  # Safe fallback
    custom_ticker = st.text_input("Custom Ticker:", placeholder="e.g. NIFTY")

if custom_ticker.strip():
    symbol = custom_ticker.strip().upper()
    if (
        not symbol.startswith("^")
        and not symbol.endswith(".NS")
        and not symbol.endswith(".BO")
    ):
        symbol += ".NS"
else:
    symbol = selected_symbol

# 2. Expiry Fetching
ticker = yf.Ticker(symbol)
try:
    expiries = ticker.options
except Exception:
    expiries = []

if expiries:
    selected_expiry = st.selectbox("Expiry Date:", options=expiries)
else:
    selected_expiry = None
    st.warning("Is symbol ke liye option chain expiries available nahi hain.")

# 3. Load Option Chain Button
if st.button("Show Option Chain", type="primary"):
    if selected_expiry:
        with st.spinner("Option Chain load ho rahi hai..."):
            try:
                opt_chain = ticker.option_chain(selected_expiry)

                # Format Calls
                calls = opt_chain.calls[
                    ["strike", "lastPrice", "openInterest", "volume"]
                ].copy()
                calls.rename(
                    columns={
                        "lastPrice": "Call Price",
                        "openInterest": "Call OI",
                        "volume": "Call Vol",
                    },
                    inplace=True,
                )

                # Format Puts
                puts = opt_chain.puts[
                    ["strike", "lastPrice", "openInterest", "volume"]
                ].copy()
                puts.rename(
                    columns={
                        "lastPrice": "Put Price",
                        "openInterest": "Put OI",
                        "volume": "Put Vol",
                    },
                    inplace=True,
                )

                # Merge both on Strike
                chain_df = pd.merge(
                    calls, puts, on="strike", how="outer"
                ).sort_values(by="strike")
                chain_df.set_index("strike", inplace=True)

                st.success(f"Option Chain for {symbol} — Expiry: {selected_expiry}")
                st.dataframe(chain_df, use_container_width=True)

            except Exception as e:
                st.error(f"Error loading option chain: {e}")
    else:
        st.error("Kripya valid expiry select karein.")
