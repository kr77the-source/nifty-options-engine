import datetime
import streamlit as st
import yfinance as yf

# Streamlit Page Config
st.set_page_config(
    page_title="3-Case Daily Bias System - F&O",
    page_icon="📈",
    layout="centered",
)

st.title("📈 3-Case Daily Bias System (F&O)")
st.write(
    "Live F&O indices aur stocks data analyze karke Buy/Sell Bias, Stop Loss aur Dynamic Targets dekhein."
)

# Top F&O Indices & Stocks Database (As per attached F&O reference)
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
    "M&M.NS",
    "NTPC.NS",
    "TITAN.NS",
    "ADANIENT.NS",
    "ADANIPORTS.NS",
    "ULTRACEMCO.NS",
    "ASIANPAINT.NS",
    "BAJAJ-AUTO.NS",
    "JSWSTEEL.NS",
]

# Built-in searchable selectbox
selected_symbol = st.selectbox(
    "F&O Stock / Index Choose Karein (Type to search):",
    options=STOCK_DATABASE,
    index=0,
)

# Optional text box agar koi dusra F&O ticker analyze karna ho
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

if st.button("Analyze Bias"):
    with st.spinner(f"Fetching live data for {symbol}..."):
        try:
            ticker = yf.Ticker(symbol)
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

                # CASE 2: Liquidity Sweep (PDH/PDL Sweep)
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

                # Volatility Range %
                range_pct = (daily_range / pdc) * 100 if pdc > 0 else 1.5

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

                elif "BEARISH SWEEP" in case2_bias or (
                    "BEARISH" in case1_bias and current_price < pdc
                ):
                    final_bias = "SELL (SHORT)"
                    entry_price = round(current_price, 2)
                    stop_loss = round(max(curr_high, pdh) * 1.002, 2)
                    target_1 = round(entry_price - (daily_range * 0.60), 2)
                    target_2 = round(
                        min(entry_price - (daily_range * 1.2), pdl), 2
                    )

                # Display Results
                st.subheader(f"Results for: {symbol}")

                col1, col2, col3 = st.columns(3)
                col1.metric("Live Price", f"₹{round(current_price, 2)}")
                col2.metric("PDH (High)", f"₹{round(pdh, 2)}")
                col3.metric("PDL (Low)", f"₹{round(pdl, 2)}")

                st.markdown("---")
                st.write(f"**[Case 1] Closing Bias:** {case1_bias}")
                st.write(f"**[Case 2] Liquidity Sweep:** {case2_bias}")
                st.write(
                    f"**[Case 3] Average Daily Volatility Range:** ₹{round(daily_range, 2)} ({round(range_pct, 2)}%)"
                )
                st.markdown("---")

                if final_bias == "BUY (LONG)":
                    st.success(f"### FINAL BIAS: {final_bias}")
                elif final_bias == "SELL (SHORT)":
                    st.error(f"### FINAL BIAS: {final_bias}")
                else:
                    st.warning(f"### FINAL BIAS: {final_bias}")

                if final_bias in ["BUY (LONG)", "SELL (SHORT)"]:
                    res_col1, res_col2 = st.columns(2)
                    res_col1.metric("Entry Price", f"₹{entry_price}")
                    res_col2.metric("Stop Loss (Strict)", f"₹{stop_loss}")

                    st.markdown("#### 🎯 Range-Calibrated Targets (F&O Rules)")
                    t_col1, t_col2 = st.columns(2)
                    t_col1.metric(
                        "Target 1 (Book 75% Profits)",
                        f"₹{target_1}",
                        delta="60% Day Range",
                    )
                    t_col2.metric(
                        "Target 2 (Opposite Liquidity Exit)",
                        f"₹{target_2}",
                        delta="Full Range Sweep",
                    )

                    st.info(
                        "💡 **F&O Target Discipline:** Indices aur F&O stocks ke liye Target 1 milte hi 75% profit book karein aur SL cost par trail kar dein."
                    )

        except Exception as e:
            st.error(f"Error processing data: {e}")
