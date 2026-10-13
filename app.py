import datetime
import pandas as pd
import streamlit as st
import yfinance as yf

# Streamlit Page Config
st.set_page_config(
    page_title="3-Case Daily Bias & Live Option Chain (₹2-3)",
    page_icon="📈",
    layout="centered",
)

st.title("📈 3-Case Daily Bias & Live Option Chain Setup")
st.write(
    "Live F&O Data aur **Real Option Chain** se ₹2-3 (Cheap OTM) options find karein."
)

# Top F&O Indices & Stocks Database
STOCK_DATABASE = [
    "^NSEI",  # Nifty 50
    "^BSESN",  # Sensex
    "^NSEBANK",  # Bank Nifty
    "HCLTECH.NS",  # HCL Technologies
    "TCS.NS",  # TCS
    "APOLLOHOSP.NS",  # Apollo Hospitals
    "RELIANCE.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "INFY.NS",
    "BHARTIARTL.NS",
    "ITC.NS",
    "SBIN.NS",
    "BAJFINANCE.NS",
    "MARUTI.NS",
    "SUNPHARMA.NS",
    "TATASTEEL.NS",
    "TATAMOTORS.NS",
    "AXISBANK.NS",
    "KOTAKBANK.NS",
]

# 1. Share / Index Selection
selected_symbol = st.selectbox(
    "1. Stock / Index Choose Karein (Type to search):",
    options=STOCK_DATABASE,
    index=0,
)

# Custom ticker input option
custom_ticker = st.text_input(
    "Ya phir koi dusra F&O Ticker yahan type karein (Optional):",
    placeholder="e.g. NIFTY or RELIANCE",
)

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

# Fetching available option expiry dates directly from Yahoo Finance Option Chain
ticker = yf.Ticker(symbol)
try:
    available_expiries = ticker.options
except Exception:
    available_expiries = []

st.markdown("---")
if available_expiries:
    selected_expiry = st.selectbox(
        "2. Option Chain Expiry Choose Karein (Live from NSE):",
        options=available_expiries,
    )
else:
    selected_expiry = None
    st.warning(
        "Is symbol ke liye live option chain expiry dates available nahi hain."
    )

if st.button("Analyze Option Chain Setup"):
    with st.spinner(f"Fetching live spot & option chain data for {symbol}..."):
        try:
            df_daily = ticker.history(period="7d", interval="1d")

            if len(df_daily) < 2:
                st.error(
                    "Error: Live data fetch nahi ho paya. Ticker symbol check karein."
                )
            else:
                prev_day = df_daily.iloc[-2]
                curr_day = df_daily.iloc[-1]

                pdh = prev_day["High"]
                pdl = prev_day["Low"]
                pdc = prev_day["Close"]

                curr_high = curr_day["High"]
                curr_low = curr_day["Low"]
                curr_close = curr_day["Close"]

                daily_range = pdh - pdl
                close_position = (
                    (pdc - pdl) / daily_range if daily_range > 0 else 0.5
                )

                # CASE 1: Daily Closing Bias
                case1_bias = "NEUTRAL"
                if close_position >= 0.70:
                    case1_bias = "BULLISH (Strong High Close)"
                elif close_position <= 0.30:
                    case1_bias = "BEARISH (Strong Low Close)"

                # CASE 2: Liquidity Sweep
                case2_bias = "NO SWEEP"
                if curr_high > pdh and curr_close < pdh:
                    case2_bias = "BEARISH SWEEP (BSL Grabbed above PDH)"
                elif curr_low < pdl and curr_close > pdl:
                    case2_bias = "BULLISH SWEEP (SSL Grabbed below PDL)"

                # CASE 3: Intraday Current Price Data
                df_15m = ticker.history(period="2d", interval="15m")
                current_price = (
                    df_15m.iloc[-1]["Close"] if not df_15m.empty else curr_close
                )

                final_bias = "NEUTRAL / NO CLEAR DIRECTION"
                entry_price = 0.0
                stop_loss = 0.0
                target_1 = 0.0
                target_2 = 0.0

                option_action = "NO TRADE"
                suggested_option = "N/A"
                found_option_price = 0.0

                # Determine Bias
                if "BULLISH SWEEP" in case2_bias or (
                    "BULLISH" in case1_bias and current_price > pdc
                ):
                    final_bias = "BUY (LONG)"
                    entry_price = round(current_price, 2)
                    stop_loss = round(min(curr_low, pdl) * 0.998, 2)
                    target_1 = round(entry_price + (daily_range * 0.60), 2)
                    target_2 = round(
                        max(entry_price + (daily_range * 1.2), pdh), 2
                    )

                    # Option Chain se Calls data fetch karein aur ₹2-3 wala strike dhoondhein
                    if selected_expiry:
                        opt_chain = ticker.option_chain(selected_expiry)
                        calls = opt_chain.calls
                        # Filter OTM calls (Strike > Current Price)
                        otm_calls = calls[calls["strike"] > current_price].copy()
                        if not otm_calls.empty:
                            # Find strike jiska lastPrice ya bid ₹2 se ₹3 ke sabse kareeb ho
                            otm_calls["diff"] = abs(otm_calls["lastPrice"] - 2.5)
                            best_row = otm_calls.loc[otm_calls["diff"].idxmin()]
                            strike_val = int(best_row["strike"])
                            found_option_price = best_row["lastPrice"]
                            option_action = "BUY OTM CALL (CE)"
                            suggested_option = (
                                f"{strike_val} CE ({selected_expiry})"
                            )

                elif "BEARISH SWEEP" in case2_bias or (
                    "BEARISH" in case1_bias and current_price < pdc
                ):
                    final_bias = "SELL (SHORT)"
                    entry_price = current_price
                    stop_loss = max(curr_high, pdh) * 1.002
                    target_1 = entry_price - (daily_range * 0.60)
                    target_2 = min(entry_price - (daily_range * 1.2), pdl)

                    # Option Chain se Puts data fetch karein aur ₹2-3 wala strike dhoondhein
                    if selected_expiry:
                        opt_chain = ticker.option_chain(selected_expiry)
                        puts = opt_chain.puts
                        # Filter OTM puts (Strike < Current Price)
                        otm_puts = puts[puts["strike"] < current_price].copy()
                        if not otm_puts.empty:
                            otm_puts["diff"] = abs(otm_puts["lastPrice"] - 2.5)
                            best_row = otm_puts.loc[otm_puts["diff"].idxmin()]
                            strike_val = int(best_row["strike"])
                            found_option_price = best_row["lastPrice"]
                            option_action = "BUY OTM PUT (PE)"
                            suggested_option = (
                                f"{strike_val} PE ({selected_expiry})"
                            )

                # Display Results
                st.subheader(f"Results for: {symbol}")

                col1, col2, col3 = st.columns(3)
                col1.metric("Live Spot Price", f"₹{round(current_price, 2)}")
                col2.metric("PDH (High)", f"₹{round(pdh, 2)}")
                col3.metric("PDL (Low)", f"₹{round(pdl, 2)}")

                st.markdown("---")
                st.write(f"**[Case 1] Closing Bias:** {case1_bias}")
                st.write(f"**[Case 2] Liquidity Sweep:** {case2_bias}")
                st.markdown("---")

                if final_bias == "BUY (LONG)":
                    st.success(f"### UNDERLYING BIAS: {final_bias}")
                elif final_bias == "SELL (SHORT)":
                    st.error(f"### UNDERLYING BIAS: {final_bias}")
                else:
                    st.warning(f"### UNDERLYING BIAS: {final_bias}")

                if final_bias in ["BUY (LONG)", "SELL (SHORT)"]:
                    st.markdown(
                        "### 🎯 **OPTION CHAIN SE FETCH KIYA GAYA ₹2-3 SETUP**"
                    )

                    opt_col1, opt_col2 = st.columns(2)
                    opt_col1.metric("Option Action", option_action)
                    opt_col2.metric(
                        "Suggested Strike (Option Chain)", suggested_option
                    )

                    st.markdown("---")
                    res_col1, res_col2 = st.columns(2)
                    res_col1.metric(
                        "Option Last Traded Price (LTP)",
                        f"₹{round(found_option_price, 2)}",
                    )
                    res_col2.metric("Spot Stop Loss", f"₹{round(stop_loss, 2)}")

                    st.markdown("#### 🎯 Spot Target Levels")
                    t_col1, t_col2 = st.columns(2)
                    t_col1.metric(
                        "Target 1 (Spot)",
                        f"₹{round(target_1, 2)}",
                        delta="60% Day Range",
                    )
                    t_col2.metric(
                        "Target 2 (Spot)",
                        f"₹{round(target_2, 2)}",
                        delta="Full Range Sweep",
                    )

                    st.info(
                        f"💡 **Option Chain Note:** Yeh strike direct live option chain se uthai gayi hai jiska current market price ₹2-3 ke sabse kareeb hai. Expiry ke din aise contracts tezi se move karte hain, par risk bhi high hota hai isliye strict discipline rakhein."
                    )

        except Exception as e:
            st.error(f"Error processing option chain data: {e}")
